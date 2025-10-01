import asyncio
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from services.google_drive_service import GoogleDriveService
from services.pinecone_service import PineconeService
from services.resume_embedding_service import ResumeEmbeddingService
from utils.logger_config import setup_logging

logger = setup_logging()

class ResumeManager:
    """Main service for managing resume ingestion and matching"""
    
    def __init__(self):
        self.drive_service = GoogleDriveService()
        self.pinecone_service = PineconeService()
        self.embedding_service = ResumeEmbeddingService()
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def ingest_all_resumes(self, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Ingest all resumes from Google Drive folder into Pinecone
        
        Args:
            folder_id: Google Drive folder ID (uses default if not provided)
            
        Returns:
            Ingestion results summary
        """
        try:
            logger.info("🚀 Starting resume ingestion process")
            
            # List all resume files (PDF and DOCX) in the folder
            resume_files = await asyncio.get_event_loop().run_in_executor(
                self.executor, self.drive_service.list_resume_files, folder_id
            )
            
            if not resume_files:
                logger.warning("⚠️ No resume files found in the specified folder")
                return {
                    'success': True,
                    'total_files': 0,
                    'processed': 0,
                    'failed': 0,
                    'message': 'No resume files found in folder'
                }
            
            logger.info(f"📁 Found {len(resume_files)} resume files to process")
            
            # Process resumes in batches
            batch_size = 5
            processed_resumes = []
            failed_files = []
            
            for i in range(0, len(resume_files), batch_size):
                batch = resume_files[i:i + batch_size]
                logger.info(f"🔄 Processing batch {i//batch_size + 1}/{(len(resume_files)-1)//batch_size + 1}")
                
                # Process batch concurrently
                batch_results = await asyncio.gather(
                    *[self._process_single_resume(file_info) for file_info in batch],
                    return_exceptions=True
                )
                
                # Collect results
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"❌ Failed to process {batch[j]['name']}: {str(result)}")
                        failed_files.append({
                            'name': batch[j]['name'],
                            'error': str(result)
                        })
                    else:
                        processed_resumes.append(result)
                        logger.info(f"✅ Successfully processed: {result['metadata']['name']}")
            
            # Batch upsert to Pinecone
            if processed_resumes:
                logger.info(f"📦 Upserting {len(processed_resumes)} resumes to Pinecone")
                await asyncio.get_event_loop().run_in_executor(
                    self.executor, 
                    self.pinecone_service.batch_upsert_resumes, 
                    processed_resumes
                )
            
            # Return summary
            result = {
                'success': True,
                'total_files': len(resume_files),
                'processed': len(processed_resumes),
                'failed': len(failed_files),
                'failed_files': failed_files,
                'message': f'Successfully processed {len(processed_resumes)} out of {len(resume_files)} resumes'
            }
            
            logger.info(f"🎉 Resume ingestion completed: {result['message']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in resume ingestion: {str(e)}")
            raise
    
    async def upload_single_resume_by_url(self, google_drive_url: str, file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a single resume from Google Drive URL to Pinecone
        
        Args:
            google_drive_url: Google Drive shareable URL
            file_name: Optional file name (will be extracted if not provided)
            
        Returns:
            Upload result summary
        """
        try:
            logger.info(f"🚀 Starting single resume upload from URL: {google_drive_url}")
            
            # Extract file ID from Google Drive URL
            file_id = self._extract_file_id_from_url(google_drive_url)
            if not file_id:
                raise ValueError("Invalid Google Drive URL format")
            
            # Get file metadata from Google Drive
            def get_file_metadata(file_id):
                return self.drive_service.service.files().get(fileId=file_id).execute()
            
            file_info = await asyncio.get_event_loop().run_in_executor(
                self.executor, 
                get_file_metadata,
                file_id
            )
            
            # Use provided file name or get from metadata
            actual_file_name = file_name or file_info.get('name', 'unknown_resume')
            
            # Validate file type
            if not self._is_supported_file_type(actual_file_name):
                raise ValueError(f"Unsupported file type. Only PDF and DOCX files are supported.")
            
            logger.info(f"📄 Processing file: {actual_file_name}")
            
            # Create file info structure similar to list_resume_files
            file_info_dict = {
                'id': file_id,
                'name': actual_file_name,
                'webViewLink': google_drive_url,
                'webContentLink': f"https://drive.google.com/uc?id={file_id}&export=download"
            }
            
            # Process the single resume
            processed_resume = await self._process_single_resume(file_info_dict)
            
            # Upload to Pinecone
            logger.info("📦 Uploading to Pinecone...")
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.pinecone_service.upsert_resume,
                processed_resume['id'],
                processed_resume['embedding'],
                processed_resume['metadata']
            )
            
            logger.info(f"✅ Successfully uploaded resume: {processed_resume['metadata']['name']}")
            
            return {
                'success': True,
                'resume_id': processed_resume['id'],
                'candidate_name': processed_resume['metadata']['name'],
                'file_name': actual_file_name,
                'message': f"Successfully uploaded resume for {processed_resume['metadata']['name']}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error uploading single resume: {str(e)}")
            return {
                'success': False,
                'resume_id': None,
                'candidate_name': None,
                'file_name': file_name or 'unknown',
                'message': f"Failed to upload resume: {str(e)}",
                'error': str(e)
            }
    
    def _extract_file_id_from_url(self, url: str) -> Optional[str]:
        """Extract Google Drive file ID from various URL formats"""
        import re
        
        # Pattern for different Google Drive URL formats
        patterns = [
            r'/file/d/([a-zA-Z0-9-_]+)',  # https://drive.google.com/file/d/FILE_ID/view
            r'id=([a-zA-Z0-9-_]+)',       # https://drive.google.com/open?id=FILE_ID
            r'/d/([a-zA-Z0-9-_]+)',       # https://docs.google.com/document/d/FILE_ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _is_supported_file_type(self, file_name: str) -> bool:
        """Check if file type is supported (PDF or DOCX)"""
        supported_extensions = ['.pdf', '.docx', '.doc']
        return any(file_name.lower().endswith(ext) for ext in supported_extensions)
    
    async def upload_resume_from_file(self, file_content: bytes, file_name: str, google_drive_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a resume from direct file content to Pinecone
        
        Args:
            file_content: File content as bytes
            file_name: Name of the file
            google_drive_url: Optional Google Drive URL for reference
            
        Returns:
            Upload result summary
        """
        try:
            logger.info(f"🚀 Starting direct file upload: {file_name}")
            
            # Validate file type
            if not self._is_supported_file_type(file_name):
                raise ValueError(f"Unsupported file type. Only PDF and DOCX files are supported.")
            
            logger.info(f"📄 Processing file: {file_name} ({len(file_content)} bytes)")
            
            # Process the resume using the embedding service
            processed_resume = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.embedding_service.process_resume,
                file_name,
                file_content,
                google_drive_url or f"direct_upload_{file_name}"
            )
            
            # Upload to Pinecone
            logger.info("📦 Uploading to Pinecone...")
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.pinecone_service.upsert_resume,
                processed_resume['id'],
                processed_resume['embedding'],
                processed_resume['metadata']
            )
            
            logger.info(f"✅ Successfully uploaded resume: {processed_resume['metadata']['name']}")
            
            return {
                'success': True,
                'resume_id': processed_resume['id'],
                'candidate_name': processed_resume['metadata']['name'],
                'file_name': file_name,
                'file_size': len(file_content),
                'google_drive_url': google_drive_url,
                'message': f"Successfully uploaded resume for {processed_resume['metadata']['name']}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error uploading file: {str(e)}")
            return {
                'success': False,
                'resume_id': None,
                'candidate_name': None,
                'file_name': file_name,
                'file_size': len(file_content) if file_content else 0,
                'google_drive_url': google_drive_url,
                'message': f"Failed to upload resume: {str(e)}",
                'error': str(e)
            }
    
    async def _process_single_resume(self, file_info: Dict) -> Dict[str, Any]:
        """
        Process a single resume file
        
        Args:
            file_info: Google Drive file information
            
        Returns:
            Processed resume data
        """
        try:
            file_id = file_info['id']
            file_name = file_info['name']
            
            # Download file content
            file_content = await asyncio.get_event_loop().run_in_executor(
                self.executor, self.drive_service.download_file_content, file_id
            )
            
            # Get shareable link
            drive_url = await asyncio.get_event_loop().run_in_executor(
                self.executor, self.drive_service.get_shareable_link, file_id
            )
            
            # Process resume
            processed_resume = await asyncio.get_event_loop().run_in_executor(
                self.executor, 
                self.embedding_service.process_resume,
                file_name, file_content, drive_url
            )
            
            return processed_resume
            
        except Exception as e:
            logger.error(f"❌ Error processing resume {file_info.get('name', 'Unknown')}: {str(e)}")
            raise
    
    async def find_matching_candidates(self, job_description: str, top_k: int = 10) -> Dict[str, Any]:
        """
        Find candidates matching the job description
        
        Args:
            job_description: Job description text
            top_k: Number of top candidates to return
            
        Returns:
            Matching candidates with scores and metadata
        """
        try:
            logger.info(f"🔍 Searching for candidates matching job description")
            
            # Generate embedding for job description
            job_embedding = await asyncio.get_event_loop().run_in_executor(
                self.executor, 
                self.embedding_service.generate_embedding,
                job_description
            )
            
            # Search similar resumes in Pinecone
            matches = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.pinecone_service.search_similar_resumes,
                job_embedding, top_k
            )
            
            # Format results for API response
            candidates = []
            for match in matches:
                candidate = {
                    'id': match['id'],
                    'name': match['metadata'].get('name', 'Unknown'),
                    'email': match['metadata'].get('email', ''),
                    'phone': match['metadata'].get('phone', ''),
                    'resume_url': match['metadata'].get('drive_url', ''),
                    'file_name': match['metadata'].get('file_name', ''),
                    'skills': match['metadata'].get('skills', []),
                    'experience_years': match['metadata'].get('experience_years', 0),
                    'job_titles': match['metadata'].get('job_titles', []),
                    'companies': match['metadata'].get('companies', []),
                    'education': match['metadata'].get('education', []),
                    'summary': match['metadata'].get('summary', ''),
                    'match_score': round(match['score'] * 100, 2),  # Convert to percentage
                    'match_explanation': self._generate_match_explanation(match['score'])
                }
                candidates.append(candidate)
            
            result = {
                'candidates': candidates,
                'total_found': len(candidates),
                'search_query': job_description[:200] + "..." if len(job_description) > 200 else job_description,
                'search_time_ms': 0  # Could add timing if needed
            }
            
            logger.info(f"✅ Found {len(candidates)} matching candidates")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error finding matching candidates: {str(e)}")
            raise
    
    def _generate_match_explanation(self, score: float) -> str:
        """Generate human-readable match explanation based on score"""
        if score >= 0.9:
            return "Excellent match - Strong alignment with job requirements"
        elif score >= 0.8:
            return "Very good match - Most requirements align well"
        elif score >= 0.7:
            return "Good match - Several key requirements match"
        elif score >= 0.6:
            return "Moderate match - Some relevant experience"
        else:
            return "Basic match - Limited alignment with requirements"
    
    async def get_resume_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored resumes
        
        Returns:
            Resume database statistics
        """
        try:
            stats = await asyncio.get_event_loop().run_in_executor(
                self.executor, self.pinecone_service.get_index_stats
            )
            
            return {
                'total_resumes': stats.get('total_vector_count', 0),
                'index_dimension': stats.get('dimension', 0),
                'index_fullness': stats.get('index_fullness', 0),
                'status': 'healthy' if stats else 'error'
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting resume stats: {str(e)}")
            return {
                'total_resumes': 0,
                'status': 'error',
                'error': str(e)
            }
    
    async def delete_all_resumes(self) -> Dict[str, Any]:
        """
        Delete all resumes from Pinecone (use with caution!)
        
        Returns:
            Deletion result
        """
        try:
            logger.warning("🧹 Deleting all resumes from database")
            
            await asyncio.get_event_loop().run_in_executor(
                self.executor, self.pinecone_service.clear_index
            )
            
            return {
                'success': True,
                'message': 'All resumes deleted successfully'
            }
            
        except Exception as e:
            logger.error(f"❌ Error deleting resumes: {str(e)}")
            raise
