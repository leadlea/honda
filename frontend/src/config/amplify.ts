import { Amplify } from 'aws-amplify';
import { environment, validateEnvironment } from './environment';

validateEnvironment();

const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: environment.cognitoUserPoolId || 'ap-northeast-1_wkRvKeooL',
      userPoolClientId: environment.cognitoClientId || '1179cu6f4a1g8hqhavmndtf8as',
      region: environment.region,
      // ★ ここを 'link' に変更
      signUpVerificationMethod: 'link' as const,
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
