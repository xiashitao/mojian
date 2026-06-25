/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ADMIN_UNLOCK_CODE?: string;
  readonly VITE_MOCK_CHAT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
