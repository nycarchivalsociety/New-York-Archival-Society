export default function handler(req, res) {
    try {
      // Your code logic (for example, fetching data, processing requests)
      res.status(200).json({ message: 'Success!' });
    } catch (error) {
      console.error('Error:', error);
      res.status(500).json({ error: 'Internal Server Error' });
    }
  }
  