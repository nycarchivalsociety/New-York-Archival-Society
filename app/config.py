import os


class Config:
    SQLALCHEMY_DATABASE_URI = 'postgresql://nyas_db_owner:ZzJqj95uBpbO@ep-odd-mud-a4gnbk1p-pooler.us-east-1.aws.neon.tech/nyas_db?sslmode=require'
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URI is not set!")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = '3fcf9348e1e66f9b4b6a28f23ae70391f54c5d7e8b2a184e72f0b2d9d6b4c3a7'
    PAYPAL_CLIENT_ID = 'Ac5maUjHXA9zaSsf0wMIrZLAuluerOgEQe3vmz8NXl8cNyedTHQbop7XXNk0yX6A7wGtRKPiITo4C1Ui'
    EMAILJS_SERVICE_ID = 'service_ogwzo2j'
    EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL = 'template_uyo2dnr'
    EMAILJS_TEMPLATE_ID_FOR_CONTACT_FORM = 'template_7813v6y'
    EMAILJS_API_ID = 'jYV8y8AwgFM2SI98x'
    RECIPIENT_EMAILS = 'nycarchivalsociety@gmail.com'
    PAYPAL_CLIENT_SECRET_KEY = 'EFRXXoXo9_Zmm0XFUJN8qCQyTbyGOW0t2H8nW4estkImteluUEN76r6GhI8RW2mvgr_I_soZmGNmiv42'
    PAYPAL_API_BASE_URL = 'https://api-m.paypal.com'
