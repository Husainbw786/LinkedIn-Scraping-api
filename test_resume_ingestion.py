#!/usr/bin/env python3
"""
Test script to ingest resumes from Google Drive to Pinecone
"""
import asyncio
import os
from dotenv import load_dotenv
from services.resume_manager import ResumeManager
from utils.logger_config import setup_logging

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logging()

async def main():
    """Main function to test resume ingestion"""
    try:
        logger.info("🚀 Starting Resume Ingestion Test")
        
        # Check environment variables
        required_vars = [
            'GOOGLE_DRIVE_CREDENTIALS_PATH',
            'GOOGLE_DRIVE_FOLDER_ID'
        ]
        
        # Check for either PINECONE_API_KEY or PINECONE_APIKEY
        if not (os.getenv('PINECONE_API_KEY') or os.getenv('PINECONE_APIKEY')):
            required_vars.append('PINECONE_API_KEY or PINECONE_APIKEY')
        
        # Check OpenAI API key
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key or openai_key == 'your_openai_api_key_here':
            logger.error("❌ OPENAI_API_KEY not set or using placeholder value")
            return
        else:
            logger.info(f"✅ OpenAI API Key found: {openai_key[:10]}...{openai_key[-4:]}")
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Missing environment variables: {missing_vars}")
            return
        
        logger.info("✅ All environment variables found")
        
        # Initialize Resume Manager
        logger.info("🔧 Initializing Resume Manager...")
        resume_manager = ResumeManager()
        
        # Get current stats
        logger.info("📊 Checking current database stats...")
        stats = await resume_manager.get_resume_stats()
        logger.info(f"Current database stats: {stats}")
        
        # Start ingestion process
        logger.info("📥 Starting resume ingestion from Google Drive...")
        result = await resume_manager.ingest_all_resumes()
        
        # Print results
        logger.info("🎉 Ingestion completed!")
        logger.info(f"Total files found: {result['total_files']}")
        logger.info(f"Successfully processed: {result['processed']}")
        logger.info(f"Failed: {result['failed']}")
        
        if result['failed_files']:
            logger.warning("Failed files:")
            for failed_file in result['failed_files']:
                logger.warning(f"  - {failed_file['name']}: {failed_file['error']}")
        
        # Get updated stats
        logger.info("📊 Getting updated database stats...")
        updated_stats = await resume_manager.get_resume_stats()
        logger.info(f"Updated database stats: {updated_stats}")
        
        logger.info("✅ Resume ingestion test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error in resume ingestion test: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
