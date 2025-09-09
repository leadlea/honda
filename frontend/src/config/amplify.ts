import { Amplify } from 'aws-amplify';
import type { ResourcesConfig } from 'aws-amplify';
import { environment, validateEnvironment } from './environment';
import { fetchAuthSession } from 'aws-amplify/auth'; // 追加

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

// Amplify v6: Auth.Cognito に region は不要
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

        // ★ 全てのRESTリクエストに Authorization を自動付与
        customHeaders: async () => {
          try {
            const s = await fetchAuthSession();
            const idToken = s.tokens?.idToken?.toString();
            // 通常の User Pools Authorizer は Bearer なしでも可。
            // Bearer が必要な構成なら下の1行に変更してください。
            // return idToken ? { Authorization: `Bearer ${idToken}` } : {};
            return idToken ? { Authorization: idToken } : {};
          } catch {
            return {};
          }
        },

        // APIキー併用時の例:
        // customHeaders: async () => {
        //   const s = await fetchAuthSession();
        //   const idToken = s.tokens?.idToken?.toString();
        //   return {
        //     ...(idToken ? { Authorization: idToken } : {}),
        //     ...(environment.apiKey ? { 'X-Api-Key': environment.apiKey } : {}),
        //   };
        // },
      },
    },
  },
};

Amplify.configure(amplifyConfig);
export default amplifyConfig;
