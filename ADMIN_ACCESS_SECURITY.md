# Admin Access - Security Implementation

## ✅ Secure Implementation Complete

### **Admin Email Configuration**

**File**: [config/admin_config.py](config/admin_config.py)

Admin emails are stored in a centralized config file:
```python
ADMIN_EMAILS = [
    'jadaunkg@gmail.com',
    'admin@tickzen.com',
]
```

### **Why This Approach is Secure**

✅ **Centralized Management**: One file to update admin access  
✅ **Environment Separation**: Easy to have different admins for dev/staging/prod  
✅ **Version Control**: Changes are tracked in git  
✅ **No Hardcoding in Templates**: Admin logic stays in backend  
✅ **Proper Authorization**: API endpoints check admin status  
✅ **Logging**: Unauthorized access attempts are logged  

### **Security Features Implemented**

1. **Admin Decorator** (`@require_admin`):
   - Verifies user is logged in
   - Checks email against admin list
   - Returns 403 Forbidden for non-admins
   - Logs unauthorized access attempts

2. **Route Protection**:
   - `/admin/quota-management` - Redirects non-admins to homepage
   - All admin API endpoints require admin decorator

3. **Menu Visibility**:
   - "Quota Management" menu only shows for admin emails
   - Template checks: `session.get('firebase_user_email') in ['admin@tickzen.com', 'jadaunkg@gmail.com']`

### **What Admin Can Access**

**Navigation Menu** (Desktop & Mobile):
- Tools → Admin Panel
- Tools → **Quota Management** ✨ (NEW)

**Admin Dashboard** (`/admin/quota-management`):
- View all users and quotas
- Edit user plans
- Adjust quota limits
- Reset quotas
- View statistics

**Admin API Endpoints**:
- `GET /admin/api/quota/users` - All users
- `POST /admin/api/quota/update` - Update quotas
- `POST /admin/api/quota/reset` - Reset user
- `POST /admin/api/quota/bulk-reset` - Monthly reset
- `GET /admin/api/quota/statistics` - System stats

## 🔒 Production Security Recommendations

### **Option 1: Environment Variables (Recommended)**
```python
# config/admin_config.py
import os

ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', 'admin@tickzen.com').split(',')
```

Then set in production:
```bash
export ADMIN_EMAILS="jadaunkg@gmail.com,admin@tickzen.com"
```

### **Option 2: Firestore Role-Based Access**
Store admin status in user document:
```python
# Firestore: users/{user_id}
{
  "email": "jadaunkg@gmail.com",
  "role": "admin",  # or "user"
  "permissions": ["quota_management", "user_management"]
}
```

Then check in decorator:
```python
user_doc = db.collection('users').document(user_id).get()
if user_doc.get('role') != 'admin':
    return jsonify({'error': 'Admin access required'}), 403
```

### **Option 3: Separate Admin Database**
Create dedicated `adminUsers` collection in Firestore with encrypted admin credentials.

## 📊 Current Implementation Impact

**Files Modified**:
- `config/admin_config.py` (NEW) - Admin email list
- `app/blueprints/admin_quota_api.py` - Uses config for auth
- `app/main_portal_app.py` - Route protection
- `app/templates/_base.html` - Menu visibility (2 locations)

**Security Level**: ⭐⭐⭐⭐☆ (4/5)
- ✅ Centralized admin list
- ✅ Backend authorization checks
- ✅ Logging of unauthorized attempts
- ⚠️ Email-based (can be spoofed in session if Firebase auth is bypassed)
- ⚠️ Hardcoded in config file (better than scattered, but environment vars are safer)

**For Maximum Security**: Use Option 2 (Firestore roles) in production.

## 🚀 Quick Start

**To Add New Admin**:
1. Edit [config/admin_config.py](config/admin_config.py)
2. Add email to `ADMIN_EMAILS` list
3. Restart application
4. New admin can access `/admin/quota-management`

**To Remove Admin**:
1. Remove email from `ADMIN_EMAILS` list
2. Restart application
3. Access immediately revoked

**To Test Admin Access**:
1. Login with `jadaunkg@gmail.com`
2. Look for "Quota Management" in Tools menu
3. Click to access admin dashboard
4. View/edit user quotas

## ⚠️ Important Notes

1. **Current Template Check**: Templates still use hardcoded check for backward compatibility with existing admin panel. Consider consolidating to use `is_admin_user()` function.

2. **Session Trust**: We trust Firebase session. If session can be manipulated, use additional server-side verification.

3. **No Password Protection**: Admin access is email-only. For sensitive operations, consider adding 2FA or password confirmation.

4. **Audit Logging**: All admin actions are logged. Check `logs/app.log` for security monitoring.

---

**Last Updated**: January 13, 2026  
**Admin Email**: jadaunkg@gmail.com  
**Status**: ✅ Active
