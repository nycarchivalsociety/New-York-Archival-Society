# api/index.py

import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()

if __name__ == '__main__':
<<<<<<< HEAD
    app.run(debug=True)
=======
    app.run()
>>>>>>> abde80176b5c71c88018e77bebbba9b0f228425c
