import { Amplify } from 'aws-amplify';
import type { ResourcesConfig } from 'aws-amplify';
import { environment, validateEnvironment } from './environment';
import { fetchAuthSession } from 'aws-amplify/auth'; // ← 追加

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

// v6 では Auth.Cognito に region は不要
const amplifyConfig: ResourcesConfig = {
  Auth: {
    Cognito: {
      userPoolId: environment.cognitoUserPoolId,
      userPoolClientId: environment.cognitoClientId,
      signUpVerificationMethod: 'link', // 要件に合わせて 'code' でもOK
      loginWith: { email: true, username: false },
    },
  },
  API: {
    REST: {
      veteranTalentAPI: {
        endpoint: environment.apiUrl,         // 例: https://xxxx.execute-api.ap-northeast-1.amazonaws.com/prod
        region: environment.region,

        // ★ ここがポイント：毎回 Authorization を自動付与
        headers: async () => {
          const s = await fetchAuthSession();
          const idToken = s.tokens?.idToken?.toString();
          // Cognito User Pools Authorizer は通常 Bearer なしでOK
          // もし Authorizer 側の設定で Bearer を要求しているなら下の1行を使ってください
          // return idToken ? { Authorization: `Bearer ${idToken}` } : {};
          return idToken ? { Authorization: idToken } : {};
        },

        // （もし API Key も併用しているなら）
        // headers: async () => {
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
