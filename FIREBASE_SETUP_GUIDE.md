# 🔥 Firebase Setup Guide for Azure Deployment

## 📋 **Step-by-Step Firebase Configuration**

### **Step 1: Create Firebase Project**

1. **Go to Firebase Console**: https://console.firebase.google.com/
2. **Click "Create a project"** or select an existing project
3. **Enter project name**: `tempautomate` (or your preferred name)
4. **Enable Google Analytics** (optional but recommended)
5. **Click "Create project"**

### **Step 2: Enable Authentication**

1. **In Firebase Console**, go to **Authentication** → **Sign-in method**
2. **Enable Email/Password** authentication:
   - Click on "Email/Password"
   - Toggle "Enable"
   - Click "Save"

3. **Enable Google** authentication (optional):
   - Click on "Google"
   - Toggle "Enable"
   - Add your authorized domain
   - Click "Save"

### **Step 3: Create Firestore Database**

1. **Go to Firestore Database** → **Create database**
2. **Choose security mode**: "Start in test mode" (for development)
3. **Select location**: Choose closest to your Azure region
4. **Click "Done"**

### **Step 4: Enable Storage**

1. **Go to Storage** → **Get started**
2. **Choose security mode**: "Start in test mode" (for development)
3. **Select location**: Same as Firestore
4. **Click "Done"**

### **Step 5: Get API Key**

1. **Go to Project Settings** (gear icon) → **General**
2. **Scroll down to "Your apps"**
3. **Click "Add app"** → **Web** (</>) 
4. **Register app** with nickname: `tempautomate-web`
5. **Copy the API Key** (starts with `AIzaSy...`)

### **Step 6: Create Service Account**

1. **Go to Project Settings** → **Service accounts**
2. **Click "Generate new private key"**
3. **Click "Generate key"**
4. **Download the JSON file**

The JSON file contains all the credentials you need:

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "abc123def456...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com",
  "client_id": "123456789012345678901",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xxxxx%40your-project.iam.gserviceaccount.com"
}
```

### **Step 7: Configure Security Rules**

#### **Firestore Security Rules**
Go to **Firestore Database** → **Rules** and add:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow users to read/write their own data
    match /userProfiles/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Allow users to manage their site profiles
    match /userSiteProfiles/{userId}/profiles/{profileId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Allow users to manage their processed tickers
    match /userSiteProfiles/{userId}/profiles/{profileId}/processedTickers/{tickerId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Allow users to manage their generated reports
    match /userGeneratedReports/{reportId} {
      allow read, write: if request.auth != null && request.auth.uid == resource.data.user_uid;
    }
    
    // Allow public read access to waitlist
    match /waitlist/{entryId} {
      allow read: if true;
      allow write: if true;
    }
  }
}
```

#### **Storage Security Rules**
Go to **Storage** → **Rules** and add:

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    // Allow users to upload files to their own folder
    match /user_ticker_files/{userId}/{profileId}/{fileName} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Allow public read access to generated reports
    match /generated_reports/{fileName} {
      allow read: if true;
      allow write: if request.auth != null;
    }
  }
}
```

## 🔧 **Required Environment Variables**

Here are all the Firebase variables you need to configure:

### **From Firebase Console (General Settings):**
- `FIREBASE_API_KEY`: Your web app API key (starts with `AIzaSy...`)

### **From Service Account JSON:**
- `FIREBASE_PROJECT_ID`: Your project ID
- `FIREBASE_PRIVATE_KEY_ID`: Private key ID
- `FIREBASE_PRIVATE_KEY`: The entire private key (with newlines escaped)
- `FIREBASE_CLIENT_EMAIL`: Service account email
- `FIREBASE_CLIENT_ID`: Client ID
- `FIREBASE_AUTH_URI`: Always `https://accounts.google.com/o/oauth2/auth`
- `FIREBASE_TOKEN_URI`: Always `https://oauth2.googleapis.com/token`
- `FIREBASE_AUTH_PROVIDER_X509_CERT_URL`: Always `https://www.googleapis.com/oauth2/v1/certs`
- `FIREBASE_CLIENT_X509_CERT_URL`: From the JSON file

## 🚀 **Quick Setup Commands**

### **Option 1: Use the Interactive Script**
```bash
chmod +x configure-azure.sh
./configure-azure.sh
```

### **Option 2: Manual Configuration**
```bash
# Set your Firebase variables (replace with your actual values)
FIREBASE_API_KEY="AIzaSyC..."
FIREBASE_PROJECT_ID="your-project-id"
FIREBASE_PRIVATE_KEY_ID="abc123def456..."
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL="firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com"
FIREBASE_CLIENT_ID="123456789012345678901"
FIREBASE_CLIENT_X509_CERT_URL="https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xxxxx%40your-project.iam.gserviceaccount.com"

# Add to Azure App Service
az webapp config appsettings set \
  --name "tempautomate-app" \
  --resource-group "tempautomate-rg" \
  --settings \
    FIREBASE_API_KEY="$FIREBASE_API_KEY" \
    FIREBASE_PROJECT_ID="$FIREBASE_PROJECT_ID" \
    FIREBASE_PRIVATE_KEY_ID="$FIREBASE_PRIVATE_KEY_ID" \
    FIREBASE_PRIVATE_KEY="$FIREBASE_PRIVATE_KEY" \
    FIREBASE_CLIENT_EMAIL="$FIREBASE_CLIENT_EMAIL" \
    FIREBASE_CLIENT_ID="$FIREBASE_CLIENT_ID" \
    FIREBASE_AUTH_URI="https://accounts.google.com/o/oauth2/auth" \
    FIREBASE_TOKEN_URI="https://oauth2.googleapis.com/token" \
    FIREBASE_AUTH_PROVIDER_X509_CERT_URL="https://www.googleapis.com/oauth2/v1/certs" \
    FIREBASE_CLIENT_X509_CERT_URL="$FIREBASE_CLIENT_X509_CERT_URL"
```

## 🔍 **Testing Firebase Configuration**

### **Test Authentication**
1. Go to your deployed app: `https://tempautomate-app.azurewebsites.net`
2. Try to register/login
3. Check Firebase Console → Authentication → Users

### **Test Firestore**
1. Create a profile in your app
2. Check Firebase Console → Firestore Database
3. Verify data is being stored

### **Test Storage**
1. Upload a file in your app
2. Check Firebase Console → Storage
3. Verify file is uploaded

## 🛡️ **Security Best Practices**

1. **Never commit Firebase credentials to Git**
2. **Use Azure Key Vault for production secrets**
3. **Enable Firebase App Check for additional security**
4. **Regularly rotate service account keys**
5. **Monitor Firebase usage and costs**

## 📊 **Firebase Pricing**

### **Free Tier Limits:**
- **Authentication**: 10,000 users/month
- **Firestore**: 1GB storage, 50,000 reads/day, 20,000 writes/day
- **Storage**: 5GB storage, 1GB downloads/day
- **Hosting**: 10GB storage, 360MB/day

### **Paid Plans:**
- **Blaze (Pay-as-you-go)**: Pay only for what you use
- **Spark (Free)**: Limited usage included

For most applications, the free tier is sufficient to start with.

## 🚨 **Troubleshooting**

### **Common Issues:**

1. **"Firebase not initialized" error**
   - Check if all environment variables are set correctly
   - Verify the private key format (should have `\n` for newlines)

2. **"Permission denied" error**
   - Check Firestore security rules
   - Verify user authentication is working

3. **"Storage bucket not found" error**
   - Check if Firebase Storage is enabled
   - Verify storage security rules

4. **"Invalid API key" error**
   - Check if the API key is correct
   - Verify the key is from the correct project

### **Debug Commands:**
```bash
# Check if Firebase variables are set
az webapp config appsettings list \
  --name "tempautomate-app" \
  --resource-group "tempautomate-rg" \
  --query "[?contains(name, 'FIREBASE')]"

# Check app logs
az webapp log tail \
  --name "tempautomate-app" \
  --resource-group "tempautomate-rg"
```

This setup will give you a fully functional Firebase backend for your Azure-deployed Flask application! 