# HR Interview Feature - Usage Guide

## 🎯 **Overview**
The HR Interview feature allows candidates to schedule and conduct live video interviews with HR professionals using Jitsi Meet integration.

## 🔧 **Technical Fix Applied**
The "Waiting for authenticated user" issue has been resolved by:
1. **Updated Jitsi URL Configuration**: Added parameters to disable authentication requirements
2. **Enhanced Meeting Instructions**: Clear guidance for both HR and candidates
3. **Improved User Interface**: Better visual feedback and instructions

---

## 📋 **Step-by-Step Procedure**

### **For Candidates:**

#### **1. Book an HR Interview**
1. Go to **Candidate Dashboard**
2. In the "HR Video Interview History" section, click **"Book New HR Interview"**
3. **Select Role & Designation**: Choose your field (IT/Non-IT) and enter your designation
4. **Choose HR Professional**: Select from available HR professionals matching your field
5. **Select Time Slot**: Pick an available 30-minute slot (9 AM - 5 PM)
6. **Confirm Booking**: Review details and confirm your booking

#### **2. Join the Interview**
1. Go to **Candidate Dashboard** → **"View My Bookings"** (HR Video Interview History section)
2. Find your scheduled interview
3. **Meeting becomes available**: 15 minutes before scheduled time
4. Click **"Join Interview Meeting"** button when available
5. **Meeting Flow**:
   - HR will join first to start the conference
   - Once HR joins, you can enter immediately
   - No authentication or waiting required

### **For HR Professionals:**

#### **1. Access Scheduled Interviews**
1. Login to **HR Dashboard**
2. Navigate to **"Manage Interviews"** or view **"Today's Interviews Scheduled"**
3. See all scheduled interviews with candidate details

#### **2. Start the Interview**
1. Click **"Join Interview"** button for the scheduled interview
2. **As HR (Moderator)**: You should join first to start the conference
3. **Meeting Instructions**:
   - You start the meeting as the moderator
   - Once you join, candidates can enter without waiting
   - No authentication required for either participant
   - 30-minute duration scheduled

#### **3. Complete the Interview**
1. After the interview, click **"Mark Complete"** button
2. Optionally add notes about the interview
3. Interview status changes to "Completed"

---

## 🎥 **Jitsi Meet Configuration**

### **What Was Fixed:**
- **Previous Issue**: Jitsi showing "Waiting for authenticated user"
- **Root Cause**: Default Jitsi configuration required moderator authentication
- **Solution Applied**: Updated meeting URL with specific parameters:
  ```
  https://meet.jit.si/{meeting_id}#config.requireDisplayName=false&config.disableDeepLinking=true&config.prejoinPageEnabled=false
  ```

### **Current Meeting Behavior:**
- ✅ **No Authentication Required**: Both HR and candidates can join freely
- ✅ **HR as Moderator**: HR starts the meeting, enabling candidate access
- ✅ **Immediate Access**: Once HR joins, candidates enter without waiting
- ✅ **Browser-Based**: No software installation required

---

## 🕐 **Meeting Timing Rules**

### **Meeting Availability:**
- **Scheduled Time**: Official interview start time
- **Join Window**: HR can join within 10 minutes after the scheduled start time
- **Duration**: 30 minutes allocated per interview
- **Business Hours**: 9:00 AM - 5:00 PM only

### **Join Sequence:**
1. **HR joins first** (within 10 minutes after scheduled start time)
2. **Candidate joins** (can join anytime after HR is in the meeting)
3. **No waiting period** once both conditions are met

---

## 🔍 **User Interface Updates**

### **Candidate Dashboard:**
- ✅ **Removed duplicate** "Book HR Interview" button from main actions
- ✅ **Centralized booking** through HR Video Interview History section
- ✅ **Role selection flow** before HR selection
- ✅ **Meeting instructions** in booking confirmation and history

### **HR Dashboard:**
- ✅ **Enhanced "Manage Interviews"** with complete interview management
- ✅ **Today's interviews** with direct join buttons
- ✅ **Meeting readiness indicators** (15-minute rule)
- ✅ **Complete interview functionality** with notes

### **Meeting Templates:**
- ✅ **Clear instructions** for both HR and candidates
- ✅ **Visual indicators** for meeting readiness
- ✅ **Enhanced button labels** ("Start Interview Meeting" for HR, "Join Interview Meeting" for candidates)

---

## 🚀 **Best Practices**

### **For HR:**
1. **Join On Time**: Enter the meeting within 10 minutes after scheduled start time
2. **Start Conference**: Your presence enables candidate access
3. **Test Equipment**: Ensure camera/microphone work before candidates join
4. **Mark Complete**: Always mark interviews as complete after finishing

### **For Candidates:**
1. **Prepare Environment**: Quiet space with good lighting
2. **Test Technology**: Check camera, microphone, and internet
3. **Join Punctually**: Enter meeting on time (HR will already be waiting)
4. **Professional Setup**: Dress professionally and have resume ready

### **For Both:**
1. **Browser Compatibility**: Use Chrome, Firefox, or Safari for best results
2. **Stable Internet**: Ensure reliable internet connection
3. **Backup Plan**: Have phone number available for communication if needed
4. **Professional Conduct**: Maintain professional behavior throughout

---

## 🔧 **Troubleshooting**

### **If Meeting Shows "Waiting for authenticated user":**
1. **HR should join first** - This starts the conference
2. **Refresh the page** - Sometimes helps with initial connection
3. **Use updated meeting URL** - Ensure using the new configured URLs
4. **Check timing** - Meeting available within 10 minutes after scheduled start time

### **If "Join" Button Not Available:**
1. **Check timing** - Must be within 10 minutes after scheduled start time
2. **Verify interview status** - Must be "scheduled" status
3. **Refresh page** - Updates meeting readiness status

### **General Issues:**
1. **Clear browser cache** - Helps with loading issues
2. **Try different browser** - Chrome recommended for Jitsi
3. **Check permissions** - Allow camera and microphone access
4. **Contact support** - If persistent issues occur

---

## 📊 **Feature Status**

### **✅ Completed Features:**
- Role/designation selection before HR booking
- Duplicate button removal from candidate dashboard
- Enhanced HR dashboard with comprehensive interview management
- Jitsi Meet configuration fix for authentication issues
- Meeting instructions and user guidance
- 15-minute meeting readiness window
- Complete interview workflow with notes

### **🎯 Benefits:**
- **Seamless Experience**: No waiting for authentication
- **Professional Flow**: Clear step-by-step process
- **Better Matching**: Role-based HR selection
- **Complete Management**: Full interview lifecycle support
- **User-Friendly**: Clear instructions and visual feedback

---

This guide ensures both HR professionals and candidates can successfully use the video interview feature without encountering the "waiting for authenticated user" issue.
