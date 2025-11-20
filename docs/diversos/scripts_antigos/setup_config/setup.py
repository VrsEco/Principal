#!/usr/bin/env python3
"""
Setup script for PEVAPP22
This script helps configure the application with database, AI, and communication services
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True
        )
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def create_env_file():
    """Create .env file from template"""
    env_file = Path(".env")
    env_example = Path("env.example")

    if env_file.exists():
        print("📄 .env file already exists")
        return True

    if env_example.exists():
        print("📄 Creating .env file from template...")
        with open(env_example, "r") as f:
            content = f.read()

        with open(env_file, "w") as f:
            f.write(content)

        print("✅ .env file created. Please edit it with your configuration.")
        return True
    else:
        print("❌ env.example file not found")
        return False


def install_dependencies():
    """Install Python dependencies"""
    return run_command(
        "pip install -r requirements.txt", "Installing Python dependencies"
    )


def setup_database():
    """Setup database"""
    print("🗄️ Setting up database...")

    # Create database directory
    db_dir = Path("instance")
    db_dir.mkdir(exist_ok=True)

    print("✅ Database directory created")
    return True


def setup_directories():
    """Create necessary directories"""
    directories = ["uploads", "temp_pdfs", "logs"]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 Created directory: {directory}")

    return True


def run_migrations():
    """Run database migrations"""
    print("🔄 Running database migrations...")

    # Initialize migration repository
    if not Path("migrations").exists():
        run_command("flask db init", "Initializing migration repository")

    # Create migration
    run_command("flask db migrate -m 'Initial migration'", "Creating initial migration")

    # Apply migration
    return run_command("flask db upgrade", "Applying database migration")


def create_admin_user():
    """Create default admin user"""
    print("👤 Creating default admin user...")

    # This will be handled by the app when it starts
    print("✅ Default admin user will be created on first run")
    return True


def main():
    """Main setup function"""
    print("🚀 PEVAPP22 Setup Script")
    print("=" * 50)

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)

    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

    # Setup steps
    steps = [
        ("Creating .env file", create_env_file),
        ("Installing dependencies", install_dependencies),
        ("Setting up directories", setup_directories),
        ("Setting up database", setup_database),
        ("Running migrations", run_migrations),
        ("Creating admin user", create_admin_user),
    ]

    failed_steps = []

    for step_name, step_function in steps:
        print(f"\n📋 {step_name}")
        if not step_function():
            failed_steps.append(step_name)

    # Summary
    print("\n" + "=" * 50)
    print("📊 Setup Summary")
    print("=" * 50)

    if failed_steps:
        print(f"❌ {len(failed_steps)} step(s) failed:")
        for step in failed_steps:
            print(f"   - {step}")
        print("\nPlease fix the errors and run the setup again.")
        return False
    else:
        print("✅ All setup steps completed successfully!")
        print("\n🎉 PEVAPP22 is ready to use!")
        print("\nNext steps:")
        print("1. Edit .env file with your configuration")
        print("2. Run: python app_new.py")
        print("3. Access: http://127.0.0.1:5002")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
