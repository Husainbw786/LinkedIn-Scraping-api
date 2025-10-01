import os
import time
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from utils.logger_config import setup_logging

logger = setup_logging()

class PineconeService:
    """Service for managing Pinecone vector database operations"""
    
    def __init__(self):
        self.api_key = os.getenv('PINECONE_API_KEY') or os.getenv('PINECONE_APIKEY')
        self.environment = os.getenv('PINECONE_ENVIRONMENT', 'gcp-starter')
        self.index_name = os.getenv('PINECONE_INDEX_NAME', 'resume')
        self.dimension = 1536  # OpenAI text-embedding-ada-002 dimensions
        
        self.pc = None
        self.index = None
        self._initialize_pinecone()
    
    def _initialize_pinecone(self):
        """Initialize Pinecone client and index"""
        try:
            if not self.api_key:
                raise ValueError("PINECONE_API_KEY not found in environment variables")
            
            # Initialize Pinecone
            self.pc = Pinecone(api_key=self.api_key)
            logger.info("✅ Pinecone client initialized successfully")
            
            # Create or connect to index
            self._setup_index()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Pinecone: {str(e)}")
            raise
    
    def _setup_index(self):
        """Create index if it doesn't exist, otherwise connect to existing index"""
        try:
            # Check if index exists
            existing_indexes = [index['name'] for index in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.info(f"📝 Creating new Pinecone index: {self.index_name}")
                
                # Create index with serverless spec for AWS (free tier)
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
                
                # Wait for index to be ready
                logger.info("⏳ Waiting for index to be ready...")
                time.sleep(10)  # Give it some time to initialize
                
                logger.info(f"✅ Index {self.index_name} created successfully")
            else:
                logger.info(f"✅ Connected to existing index: {self.index_name}")
            
            # Connect to the index
            self.index = self.pc.Index(self.index_name)
            
        except Exception as e:
            logger.error(f"❌ Error setting up Pinecone index: {str(e)}")
            raise
    
    def upsert_resume(self, resume_id: str, embedding: List[float], metadata: Dict[str, Any]):
        """
        Upsert a resume embedding with metadata to Pinecone
        
        Args:
            resume_id: Unique identifier for the resume
            embedding: Vector embedding of the resume
            metadata: Resume metadata (name, skills, experience, drive_url, etc.)
        """
        try:
            # Prepare vector for upsert
            vector = {
                'id': resume_id,
                'values': embedding,
                'metadata': metadata
            }
            
            # Upsert to Pinecone
            self.index.upsert(vectors=[vector])
            logger.info(f"✅ Resume {resume_id} upserted to Pinecone successfully")
            
        except Exception as e:
            logger.error(f"❌ Error upserting resume {resume_id}: {str(e)}")
            raise
    
    def batch_upsert_resumes(self, resumes: List[Dict[str, Any]], batch_size: int = 100):
        """
        Batch upsert multiple resumes to Pinecone
        
        Args:
            resumes: List of resume dictionaries with id, embedding, and metadata
            batch_size: Number of vectors to upsert in each batch
        """
        try:
            total_resumes = len(resumes)
            logger.info(f"📦 Starting batch upsert of {total_resumes} resumes")
            
            for i in range(0, total_resumes, batch_size):
                batch = resumes[i:i + batch_size]
                
                # Prepare vectors for batch upsert
                vectors = []
                for resume in batch:
                    vector = {
                        'id': resume['id'],
                        'values': resume['embedding'],
                        'metadata': resume['metadata']
                    }
                    vectors.append(vector)
                
                # Upsert batch
                self.index.upsert(vectors=vectors)
                logger.info(f"✅ Batch {i//batch_size + 1}/{(total_resumes-1)//batch_size + 1} upserted successfully")
            
            logger.info(f"🎉 All {total_resumes} resumes upserted successfully")
            
        except Exception as e:
            logger.error(f"❌ Error in batch upsert: {str(e)}")
            raise
    
    def search_similar_resumes(self, query_embedding: List[float], top_k: int = 10, 
                             filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Search for similar resumes based on query embedding
        
        Args:
            query_embedding: Vector embedding of the job description
            top_k: Number of top results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of matching resumes with scores and metadata
        """
        try:
            # Perform vector search
            search_results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                include_values=False,
                filter=filter_metadata
            )
            
            # Format results
            matches = []
            for match in search_results.matches:
                result = {
                    'id': match.id,
                    'score': float(match.score),
                    'metadata': dict(match.metadata)
                }
                matches.append(result)
            
            logger.info(f"🔍 Found {len(matches)} matching resumes")
            return matches
            
        except Exception as e:
            logger.error(f"❌ Error searching resumes: {str(e)}")
            raise
    
    def delete_resume(self, resume_id: str):
        """
        Delete a resume from Pinecone index
        
        Args:
            resume_id: ID of the resume to delete
        """
        try:
            self.index.delete(ids=[resume_id])
            logger.info(f"🗑️ Resume {resume_id} deleted successfully")
            
        except Exception as e:
            logger.error(f"❌ Error deleting resume {resume_id}: {str(e)}")
            raise
    
    def get_index_stats(self) -> Dict:
        """
        Get statistics about the Pinecone index
        
        Returns:
            Index statistics dictionary
        """
        try:
            stats = self.index.describe_index_stats()
            return {
                'total_vector_count': stats.total_vector_count,
                'dimension': stats.dimension,
                'index_fullness': stats.index_fullness
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting index stats: {str(e)}")
            return {}
    
    def clear_index(self):
        """
        Clear all vectors from the index (use with caution!)
        """
        try:
            self.index.delete(delete_all=True)
            logger.warning("🧹 All vectors cleared from index")
            
        except Exception as e:
            logger.error(f"❌ Error clearing index: {str(e)}")
            raise
