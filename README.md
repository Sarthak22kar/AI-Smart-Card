# 🤖 AI Smart Visiting Card Network & Service Recommendation System

An intelligent system that converts physical visiting cards into a smart digital professional network capable of recommending trusted contacts based on context, reputation, and geographic suitability.

## 🚀 Features

### ✅ Implemented Core Features

- **📷 Advanced OCR Scanning**: Extract comprehensive contact information from both sides of visiting cards using Google Gemini 2.5 Flash (95-99% accuracy)
- **🎯 Automatic Background Removal**: AI-powered card detection removes backgrounds and straightens angled cards
- **🖼️ Universal Image Format Support**: JPG, PNG, HEIC, HEIF, WebP, TIFF, BMP, GIF, SVG
- **🔧 Multi-Engine OCR**: Gemini 2.5 Flash → EasyOCR → Tesseract fallback for maximum reliability
- **🧠 AI-Powered Recommendations**: Intelligent service recommendations using multi-factor scoring algorithm
- **📇 Smart Contact Management**: Organized contact database with detailed professional information
- **🔍 Search & Filter**: Find contacts by name, profession, or service type
- **📊 Professional Scoring**: Rank contacts based on review scores, response rates, and location suitability
- **💼 Professional Network**: Build and maintain your trusted professional network
- **🚫 Duplicate Detection**: Prevents saving duplicate contacts automatically

### 🎯 Key Innovations

1. **Google Gemini 2.5 Flash Integration** - State-of-the-art OCR with 95-99% accuracy
2. **Automatic Card Detection** - Removes backgrounds and corrects perspective automatically
3. **Context-Aware Need Detection Engine** - Detects service needs from user search queries
4. **Multi-Source Professional Credibility Ranking** - Combines contact data with scoring metrics
5. **Geo-Practical Service Recommendation** - Recommends professionals based on practical distance
6. **Smart Contact Extraction** - Advanced NLP parsing for phones, emails, professions, companies

## 🏗️ System Architecture

```
Frontend (React + TypeScript)
├── UploadCard Component (Two-sided card scanning)
├── ContactList Component (Professional network display)
├── Recommendation Component (AI-powered service search)
└── Smart UI with real-time updates

Backend (FastAPI + Python)
├── OCR Engine (Gemini 2.5 Flash → EasyOCR → Tesseract)
├── Card Detection (OpenCV-based background removal)
├── AI Recommendation System (Multi-factor scoring)
├── SQLite Database (Contact management)
└── RESTful API (CORS-enabled)

Data Flow:
Card Images → Background Removal → OCR Extraction → Field Parsing → 
Database Storage → AI Recommendations
```

## 🛠️ Technology Stack

- **Frontend**: React, TypeScript, Vite
- **Backend**: Python, FastAPI, Uvicorn
- **OCR**: Google Gemini 2.5 Flash API, EasyOCR, Tesseract OCR
- **Image Processing**: OpenCV, PIL, pillow-heif
- **NLP**: spaCy (for name extraction)
- **Database**: SQLite

## 📋 Installation & Setup

### Prerequisites

- Python 3.8+ with pip
- Node.js 16+ with npm
- Tesseract OCR installed
- Google Gemini API key (free tier: 250 requests/day)

### Quick Start

**Option 1: Use Startup Script (Recommended)**

```bash
# Make script executable (first time only)
chmod +x START_SYSTEM.sh STOP_SYSTEM.sh

# Start the system
./START_SYSTEM.sh

# Open browser to http://localhost:5173

# Stop the system when done
./STOP_SYSTEM.sh
```

**Option 2: Manual Setup**

### Backend Setup

1. **Install Python dependencies**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Install Tesseract OCR**:
   - **macOS**: `brew install tesseract`
   - **Ubuntu**: `sudo apt install tesseract-ocr`
   - **Windows**: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

3. **Configure API Keys**:
   - Edit `backend/.env` and add your Gemini API key:
   ```bash
   GEMINI_API_KEY=your_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```

4. **Start the backend server**:
   ```bash
   uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

### Frontend Setup

1. **Install Node.js dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server**:
   ```bash
   npm run dev
   ```

3. **Open your browser**: Navigate to `http://localhost:5173`

## 🎮 How to Use

### 1. Scan Visiting Cards
- Upload both front and back images of visiting cards
- The AI will automatically:
  - Remove background and straighten the card
  - Extract text using Gemini 2.5 Flash OCR (95-99% accuracy)
  - Parse 8 fields: Name, Phone, Email, Designation, Company, Address, Website, GSTIN
- View extracted information before saving to your network

### 2. Build Your Professional Network
- All scanned contacts are automatically organized
- View detailed contact information by clicking on contacts
- See profession tags and contact details
- Search contacts by name, company, or designation

### 3. Get AI Recommendations
- Search for any service (e.g., "plumber", "lawyer", "doctor")
- Get ranked recommendations based on:
  - Review scores (30%)
  - Response rates (20%)
  - Website presence (15%)
  - Customer interaction (15%)
  - Location suitability (10%)
  - Service completion (10%)

## 📊 Scoring Algorithm

The AI recommendation system uses a weighted scoring algorithm:

```python
Final Score = (Review Score * 0.30) + 
              (Response Rate * 0.20) + 
              (Website Presence * 0.15) + 
              (Customer Interaction * 0.15) + 
              (Location Suitability * 0.10) + 
              (Service Completion * 0.10)
```

## 🔧 API Endpoints

- `GET /` - Health check
- `POST /scan-card/` - Upload and process visiting card images (front + back)
- `GET /contacts/` - Retrieve all contacts
- `GET /contacts/{id}` - Get specific contact details
- `DELETE /contacts/{id}` - Delete a contact
- `GET /recommend/{service}` - Get AI recommendations for a service
- `GET /search/?query=...` - Search contacts by name, company, or profession
- `GET /stats/` - Get database statistics
- `GET /formats/` - Get supported image formats and recommendations

## 📁 Project Structure

```
├── backend/
│   ├── main.py              # FastAPI application & API endpoints
│   ├── ocr.py              # OCR engine manager (Gemini/EasyOCR/Tesseract)
│   ├── gemini_ocr.py       # Google Gemini 2.5 Flash integration
│   ├── smart_extractor.py  # Field extraction & NLP parsing
│   ├── card_detector.py    # Background removal & card detection
│   ├── recommendation.py    # AI recommendation engine
│   ├── database.py         # Database operations
│   ├── config.py           # Configuration settings
│   ├── .env                # Environment variables (API keys)
│   ├── requirements.txt    # Python dependencies
│   └── contacts.db         # SQLite database
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── App.tsx        # Main application
│   │   └── main.tsx       # Entry point
│   ├── package.json       # Node.js dependencies
│   └── vite.config.ts     # Vite configuration
├── START_SYSTEM.sh         # Start backend + frontend
├── STOP_SYSTEM.sh          # Stop all services
├── README.md              # This file
├── COMPLETE_SYSTEM_WORKFLOW.md  # Detailed workflow documentation
├── GEMINI_INTEGRATION_GUIDE.md  # Gemini API guide
├── CARD_DETECTION_GUIDE.md      # Background removal guide
├── HOW_TO_START_SYSTEM.md       # Startup guide
└── QUICK_COMMANDS.md            # Quick reference
```

## 🚀 Future Enhancements

- **📱 Mobile App**: React Native implementation
- **🌐 Web Scraping**: Automatic online reputation analysis
- **📍 Location Services**: Google Maps integration for distance calculation
- **🔔 Notifications**: Smart service reminders and suggestions
- **🤝 Referral System**: Professional referral marketplace
- **📈 Analytics**: Contact interaction tracking and insights
- **🔄 Batch Processing**: Upload multiple cards at once
- **🌍 Multi-language Support**: OCR for non-English cards

## 🐛 Troubleshooting

### Common Issues

1. **Backend not running**: 
   - Run `./START_SYSTEM.sh` or manually start with `cd backend && uvicorn main:app --reload`
   
2. **"Network error: Load failed"**: 
   - Restart system: `./STOP_SYSTEM.sh && ./START_SYSTEM.sh`
   - Check backend is running on http://127.0.0.1:8000
   
3. **Tesseract not found**: 
   - Ensure Tesseract is installed and path is correct in `ocr.py`
   
4. **CORS errors**: 
   - Backend CORS is configured for all origins in development
   
5. **File upload fails**: 
   - Check file size limits and supported formats
   - Ensure both front and back images are selected
   
6. **OCR accuracy low**: 
   - Ensure good image quality and proper lighting
   - Check Gemini API key is configured correctly
   - Verify API quota (250 requests/day on free tier)
   
7. **Duplicate contact error**: 
   - System prevents duplicates by name, phone, or email
   - Delete existing contact if you want to re-scan

### Development Tips

- Use high-quality, well-lit images for better OCR results
- Test with various card layouts and fonts
- Monitor backend logs: `tail -f backend.log`
- Check frontend logs: `tail -f frontend.log`
- View database: `cd backend && python view_contacts.py`

### Getting Help

For detailed documentation, see:
- **Complete Workflow**: `COMPLETE_SYSTEM_WORKFLOW.md`
- **Gemini Integration**: `GEMINI_INTEGRATION_GUIDE.md`
- **Card Detection**: `CARD_DETECTION_GUIDE.md`
- **Startup Guide**: `HOW_TO_START_SYSTEM.md`
- **Quick Commands**: `QUICK_COMMANDS.md`

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

---

**Built with ❤️ using AI-powered development tools**# AI-Smart-Card
