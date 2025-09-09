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

// v6: Auth.Cognito に region は不要
const amplifyConfig: ResourcesConfig = {
  Auth: {
    Cognito: {
      userPoolId: environment.cognitoUserPoolId,
      userPoolClientId: environment.cognitoClientId,
      signUpVerificationMethod: 'link', // 必要に応じて 'code'
      loginWith: { email: true, username: false },
    },
  },
  API: {
    REST: {
      veteranTalentAPI: {
        endpoint: environment.apiUrl, // 例: https://xxxx.execute-api.ap-northeast-1.amazonaws.com/prod
        region: environment.region,
        // ※ ここに headers/customHeaders は入れない（型エラーになるため）
      },
    },
  },
};

Amplify.configure(amplifyConfig);
export default amplifyConfig;
