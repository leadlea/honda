import { Amplify } from 'aws-amplify';
import type { ResourcesConfig } from 'aws-amplify';
import { environment, validateEnvironment } from './environment';

// 必須チェック
validateEnvironment();
const assertNonEmpty = (name: string, v?: string) => {
  if (!v || v === 'ap-northeast-1_placeholder' || v === 'placeholder-client-id') {
    throw new Error(`[Amplify] Missing or placeholder value: ${name}`);
  }
};
assertNonEmpty('region', environment.region);
assertNonEmpty('cognitoUserPoolId', environment.cognitoUserPoolId);
assertNonEmpty('cognitoClientId', environment.cognitoClientId);
assertNonEmpty('apiUrl', environment.apiUrl);

// v6 では Auth.Cognito に region は不要（型外）
const amplifyConfig: ResourcesConfig = {
  Auth: {
    Cognito: {
      userPoolId: environment.cognitoUserPoolId,
      userPoolClientId: environment.cognitoClientId,
      signUpVerificationMethod: 'link',
      loginWith: { email: true, username: false },
      // ← region は削除
    },
  },
  API: {
    REST: {
      veteranTalentAPI: {
        endpoint: environment.apiUrl,
        region: environment.region, // ここは必要
      },
    },
  },
};

Amplify.configure(amplifyConfig);
export default amplifyConfig;
