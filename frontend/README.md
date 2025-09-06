# Honda Veteran Talent Bank - Frontend

React.js frontend application for the Honda Veteran Talent Matching system.

## Features Implemented (Task 9.1)

### Authentication & User Management UI
- ✅ Cognito integrated login/logout screens
- ✅ User profile display and editing screens  
- ✅ Role-based access control (RBAC)
- ✅ User registration with email verification
- ✅ Responsive design for mobile and desktop

### Components Structure

```
src/
├── components/
│   ├── auth/
│   │   ├── AuthPage.tsx          # Main auth container
│   │   ├── LoginForm.tsx         # Login form component
│   │   ├── SignUpForm.tsx        # Registration form component
│   │   └── AuthForms.css         # Auth styling
│   ├── common/
│   │   ├── ProtectedRoute.tsx    # Route protection by role
│   │   └── RoleBasedComponent.tsx # Conditional rendering by role
│   ├── dashboard/
│   │   ├── Dashboard.tsx         # Main dashboard
│   │   └── Dashboard.css         # Dashboard styling
│   ├── layout/
│   │   ├── Header.tsx            # Navigation header
│   │   ├── Header.css            # Header styling
│   │   ├── Layout.tsx            # Main layout wrapper
│   │   └── Layout.css            # Layout styling
│   └── profile/
│       ├── UserProfile.tsx       # User profile management
│       └── UserProfile.css       # Profile styling
├── contexts/
│   └── AuthContext.tsx           # Authentication state management
├── services/
│   └── authService.ts            # AWS Cognito integration
├── types/
│   └── auth.ts                   # TypeScript type definitions
└── config/
    └── amplify.ts                # AWS Amplify configuration
```

## User Roles & Permissions

### Veteran (ベテラン社員)
- Access to questionnaire system
- Profile management
- View recommendations
- Track application status

### External Recruiter (外部リクルーター)  
- Search public veteran profiles
- Contact veterans through platform
- View filtered search results

### Admin (管理者)
- System administration
- User management
- Full access to all features

## Environment Setup

1. Copy environment template:
```bash
cp .env.example .env
```

2. Configure AWS Cognito settings:
```env
REACT_APP_AWS_REGION=us-east-1
REACT_APP_USER_POOL_ID=your_user_pool_id
REACT_APP_USER_POOL_CLIENT_ID=your_client_id
REACT_APP_API_ENDPOINT=https://your-api-gateway-url
```

## Development

```bash
# Install dependencies
npm install

# Start development server
npm start

# Type checking
npm run type-check

# Build for production
npm run build

# Run tests
npm test
```

## Key Features

### Authentication Flow
1. **Login**: Email/password authentication via AWS Cognito
2. **Registration**: New user signup with email verification
3. **Session Management**: Automatic token refresh and validation
4. **Role Assignment**: Users assigned roles during registration

### Role-Based Access Control
- **ProtectedRoute**: Wraps components requiring authentication
- **RoleBasedComponent**: Conditionally renders content based on user role
- **Navigation**: Dynamic menu items based on user permissions

### User Profile Management
- **View Profile**: Display user information and role
- **Edit Profile**: Update name, department, employee ID
- **Status Tracking**: Show account creation and last update dates

### Responsive Design
- Mobile-first approach
- Tablet and desktop optimizations
- Touch-friendly interface elements
- Accessible color contrast and typography

## Next Steps

The following features will be implemented in subsequent tasks:
- AI Questionnaire System (Task 9.2)
- Profile Management UI (Task 9.2) 
- Recommendations & Matching UI (Task 9.3)
- External Platform UI (Task 9.4)

## Requirements Satisfied

This implementation satisfies the following requirements:
- **1.1**: User authentication and session management
- **1.4**: User profile updates and management
- **5.1, 5.2, 5.3, 5.4**: Role-based access control and security
- **7.1, 7.2**: User profile visibility and privacy controls