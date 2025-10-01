import os
import io
from typing import List, Dict, Optional, Any
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from utils.logger_config import setup_logging

logger = setup_logging()

class GoogleDriveService:
    """Service for interacting with Google Drive API"""
    
    def __init__(self):
        self.credentials_path = os.getenv('GOOGLE_DRIVE_CREDENTIALS_PATH')
        self.folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        self.service = None
        self.is_available = False
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive service with credentials"""
        try:
            if not self.credentials_path or not os.path.exists(self.credentials_path):
                raise FileNotFoundError(f"Google Drive credentials not found at: {self.credentials_path}")
            
            # Define the scope for Google Drive API
            SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
            
            # Load credentials from service account file
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES
            )
            
            # Build the service
            self.service = build('drive', 'v3', credentials=credentials)
            
            self.is_available = True
            logger.info("✅ Google Drive service initialized successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ Google Drive service not available: {str(e)}")
            logger.warning("Google Drive functionality will be disabled")
            self.is_available = False
            self.service = None
    
    def list_resume_files(self, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all resume files (PDF and DOCX) in the specified Google Drive folder
        
        Args:
            folder_id: Google Drive folder ID (uses default if not provided)
        Returns:
            List of file metadata dictionaries
        """
        if not self.is_available:
            logger.warning("Google Drive service not available")
            return []
        try:
            folder_id = folder_id or self.folder_id
            if not folder_id:
                raise ValueError("No folder ID provided")
            
            # Query to find both PDF and DOCX files in the specified folder
            query = f"'{folder_id}' in parents and (mimeType='application/pdf' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document') and trashed=false"
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, size, modifiedTime, webViewLink, webContentLink)",
                pageSize=100
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"📁 Found {len(files)} resume files (PDF/DOCX) in Google Drive folder")
            
            return files
            
        except Exception as e:
            logger.error(f"❌ Error listing resume files: {str(e)}")
            raise
    
    def download_file_content(self, file_id: str, max_retries: int = 3) -> bytes:
        """
        Download file content from Google Drive
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            File content as bytes
        """
        if not self.is_available:
            raise RuntimeError("Google Drive service not available")
            
        import time
        
        for attempt in range(max_retries):
            try:
                # Get file metadata first
                file_metadata = self.service.files().get(fileId=file_id).execute()
                logger.info(f"📥 Downloading file: {file_metadata.get('name', 'Unknown')} (attempt {attempt + 1})")
                
                # Download file content
                request = self.service.files().get_media(fileId=file_id)
                file_io = io.BytesIO()
                downloader = MediaIoBaseDownload(file_io, request)
                
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.debug(f"Download progress: {int(status.progress() * 100)}%")
                
                file_content = file_io.getvalue()
                logger.info(f"✅ Successfully downloaded {len(file_content)} bytes")
                
                return file_content
                
            except Exception as e:
                logger.warning(f"⚠️ Download attempt {attempt + 1} failed for file {file_id}: {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.info(f"⏳ Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ All {max_retries} download attempts failed for file {file_id}")
                    raise
    
    def get_shareable_link(self, file_id: str) -> str:
        """
        Get shareable link for a file
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Shareable URL for the file
        """
        try:
            file_metadata = self.service.files().get(
                fileId=file_id, 
                fields='webViewLink'
            ).execute()
            
            return file_metadata.get('webViewLink', '')
            
        except Exception as e:
            logger.error(f"❌ Error getting shareable link for file {file_id}: {str(e)}")
            return ""
    
    def get_file_metadata(self, file_id: str) -> Dict:
        """
        Get detailed metadata for a specific file
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            File metadata dictionary
        """
        try:
            metadata = self.service.files().get(
                fileId=file_id,
                fields="id, name, size, mimeType, modifiedTime, webViewLink, webContentLink"
            ).execute()
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Error getting file metadata for {file_id}: {str(e)}")
            return {}
