#!/usr/bin/env python3
"""
Password Reset Script for BirdWeatherViz3

This script can be run inside the Docker container to reset the configuration password.

Usage:
    # Interactive mode (prompts for password):
    docker exec -it birdweatherviz3-backend-1 python reset_password.py

    # With password argument:
    docker exec birdweatherviz3-backend-1 python reset_password.py --password "new-secure-password"

    # Reset to environment variable default:
    docker exec birdweatherviz3-backend-1 python reset_password.py --reset-to-default
"""

import argparse
import sys
import getpass


def reset_password(new_password: str) -> None:
    """Set a new password hash in the database."""
    from app.api.deps import set_password_hash

    if len(new_password) < 8:
        print("Error: Password must be at least 8 characters long")
        sys.exit(1)

    set_password_hash(new_password)
    print("Password has been reset successfully!")
    print("The new password is now stored securely in the database.")


def reset_to_default() -> None:
    """Remove the custom password, reverting to environment variable."""
    from app.db.session import get_db
    from app.db.models.setting import Setting
    from app.api.deps import PASSWORD_SETTING_KEY

    db = next(get_db())
    try:
        setting = db.query(Setting).filter(Setting.key == PASSWORD_SETTING_KEY).first()
        if setting:
            db.delete(setting)
            db.commit()
            print("Custom password removed.")
            print("The system will now use the CONFIG_PASSWORD environment variable.")
        else:
            print("No custom password was set. Already using environment variable.")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Reset the BirdWeatherViz3 configuration password",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Interactive mode:
    python reset_password.py

  Set specific password:
    python reset_password.py --password "my-new-secure-password"

  Reset to environment variable:
    python reset_password.py --reset-to-default
        """
    )
    parser.add_argument(
        "--password", "-p",
        help="New password to set (must be at least 8 characters)"
    )
    parser.add_argument(
        "--reset-to-default", "-r",
        action="store_true",
        help="Remove custom password and revert to CONFIG_PASSWORD environment variable"
    )

    args = parser.parse_args()

    if args.reset_to_default:
        reset_to_default()
    elif args.password:
        reset_password(args.password)
    else:
        # Interactive mode
        print("BirdWeatherViz3 Password Reset")
        print("=" * 40)
        print()
        print("Options:")
        print("1. Set a new password")
        print("2. Reset to default (environment variable)")
        print("3. Cancel")
        print()

        choice = input("Enter choice (1-3): ").strip()

        if choice == "1":
            print()
            new_password = getpass.getpass("Enter new password (min 8 characters): ")
            if not new_password:
                print("Error: Password cannot be empty")
                sys.exit(1)
            confirm_password = getpass.getpass("Confirm new password: ")
            if new_password != confirm_password:
                print("Error: Passwords do not match")
                sys.exit(1)
            reset_password(new_password)
        elif choice == "2":
            reset_to_default()
        else:
            print("Cancelled.")
            sys.exit(0)


if __name__ == "__main__":
    main()
