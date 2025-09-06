// Environment configuration for Honda Veteran Talent Matching Frontend
// This file manages environment variables and API endpoints

export interface EnvironmentConfig {
  apiUrl: string;
  cognitoUserPoolId: string;
  cognitoClientId: string;
  region: string;
  stage: string;
  isDevelopment: boolean;
  isProduction: boolean;
}

// Get environment variables with fallbacks
const getEnvVar = (key: string, defaultValue: string = ''): string => {
  return process.env[key] || defaultValue;
};

// Environment configuration
export const environment: EnvironmentConfig = {
  apiUrl: getEnvVar('REACT_APP_API_URL', 'http://localhost:3001'),
  cognitoUserPoolId: getEnvVar('REACT_APP_COGNITO_USER_POOL_ID', ''),
  cognitoClientId: getEnvVar('REACT_APP_COGNITO_CLIENT_ID', ''),
  region: getEnvVar('REACT_APP_REGION', 'us-west-2'),
  stage: getEnvVar('REACT_APP_STAGE', 'dev'),
  isDevelopment: process.env.NODE_ENV === 'development',
  isProduction: process.env.NODE_ENV === 'production',
};

// Validation function to ensure required environment variables are set
export const validateEnvironment = (): void => {
  const requiredVars = [
    'REACT_APP_API_URL',
    'REACT_APP_COGNITO_USER_POOL_ID', 
    'REACT_APP_COGNITO_CLIENT_ID'
  ];

  const missingVars = requiredVars.filter(varName => !process.env[varName]);

  if (missingVars.length > 0 && environment.isProduction) {
    console.error('Missing required environment variables:', missingVars);
    throw new Error(`Missing required environment variables: ${missingVars.join(', ')}`);
  }

  if (missingVars.length > 0 && environment.isDevelopment) {
    console.warn('Missing environment variables (using defaults):', missingVars);
  }
};

// API endpoints configuration
export const apiEndpoints = {
  // Authentication endpoints
  auth: {
    login: `${environment.apiUrl}/auth/login`,
    logout: `${environment.apiUrl}/auth/logout`,
    profile: `${environment.apiUrl}/auth/profile`,
    permissions: `${environment.apiUrl}/auth/permissions`,
  },

  // Profile management endpoints
  profiles: {
    get: (userId: string) => `${environment.apiUrl}/profiles/${userId}`,
    update: (userId: string) => `${environment.apiUrl}/profiles/${userId}`,
    privacy: (userId: string) => `${environment.apiUrl}/profiles/${userId}/privacy`,
    businessTitle: (userId: string) => `${environment.apiUrl}/profiles/${userId}/business-title`,
  },

  // Questionnaire endpoints
  questionnaire: {
    get: (userId: string) => `${environment.apiUrl}/questionnaire/${userId}`,
    submit: (userId: string) => `${environment.apiUrl}/questionnaire/${userId}/submit`,
    history: (userId: string) => `${environment.apiUrl}/questionnaire/${userId}/history`,
    regenerate: (userId: string) => `${environment.apiUrl}/questionnaire/${userId}/regenerate`,
  },

  // Recommendations endpoints
  recommendations: {
    get: (userId: string) => `${environment.apiUrl}/recommendations/${userId}`,
  },

  // Applications endpoints
  applications: {
    create: (userId: string) => `${environment.apiUrl}/applications/${userId}`,
    updateStatus: (applicationId: string) => `${environment.apiUrl}/applications/${applicationId}/status`,
  },

  // Opportunities endpoints
  opportunities: {
    search: `${environment.apiUrl}/opportunities/search`,
  },

  // Public platform endpoints
  public: {
    search: `${environment.apiUrl}/public/veterans/search`,
    profile: (profileId: string) => `${environment.apiUrl}/public/veterans/${profileId}`,
    contact: (profileId: string) => `${environment.apiUrl}/public/contact/${profileId}`,
    categories: `${environment.apiUrl}/public/categories`,
  },
};

// Cognito configuration for AWS Amplify
export const cognitoConfig = {
  region: environment.region,
  userPoolId: environment.cognitoUserPoolId,
  userPoolWebClientId: environment.cognitoClientId,
  mandatorySignIn: true,
  authenticationFlowType: 'USER_PASSWORD_AUTH',
};

// Export for debugging in development
if (environment.isDevelopment) {
  console.log('Environment Configuration:', {
    ...environment,
    cognitoUserPoolId: environment.cognitoUserPoolId ? '***' : 'NOT SET',
    cognitoClientId: environment.cognitoClientId ? '***' : 'NOT SET',
  });
}