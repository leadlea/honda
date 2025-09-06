import { Amplify } from 'aws-amplify';
import { environment, validateEnvironment } from './environment';

// Validate environment variables
validateEnvironment();

const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: environment.cognitoUserPoolId || 'us-west-2_XXXXXXXXX',
      userPoolClientId: environment.cognitoClientId || 'xxxxxxxxxxxxxxxxxxxxxxxxxx',
      region: environment.region,
      signUpVerificationMethod: 'code' as const,
      loginWith: {
        email: true,
        username: false,
      },
    },
  },
  API: {
    REST: {
      veteranTalentAPI: {
        endpoint: environment.apiUrl,
        region: environment.region,
      },
    },
  },
};

Amplify.configure(amplifyConfig);

export default amplifyConfig;