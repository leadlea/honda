import { useEffect } from "react";

export default function Verified() {
  useEffect(() => {
    const t = setTimeout(() => {
      // ログイン画面（トップ）へ戻す
      window.location.assign("/");
    }, 2500);
    return () => clearTimeout(t);
  }, []);

  return (
    <div style={{ padding: 32, textAlign: "center" }}>
      <h2>メール確認が完了しました</h2>
      <p>数秒後にログイン画面へ移動します…</p>
    </div>
  );
}
