"""
Script d'initialisation de la base de données.
Crée un utilisateur admin par défaut.
"""
import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import AsyncSessionLocal
from app.repositories.user_repository import UserRepository
import bcrypt

# Use bcrypt directly to avoid passlib compatibility issues
def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


async def init_db():
    """Initialize database with default admin user"""
    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        
        # Check if admin exists - if yes, delete and recreate with new bcrypt hash
        admin = await user_repo.get_by_username("admin")
        
        if admin:
            print("Deleting existing admin user...")
            await user_repo.delete(admin.user_id)
            await session.commit()
        
        print("Creating default admin user...")
        hashed_password = hash_password("admin123")
        
        await user_repo.create(
            username="admin",
            email="admin@ubuntuairlab.com",
            hashed_password=hashed_password,
            full_name="System Administrator",
            role="admin"
        )
        
        print("✓ Admin user created (username: admin, password: admin123)")


if __name__ == "__main__":
    asyncio.run(init_db())
