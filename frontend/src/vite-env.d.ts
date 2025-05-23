/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string;
  readonly DEV: boolean;
  readonly SSR: boolean;
  readonly BASE_URL: string;
  readonly MODE: string;
  readonly PROD: boolean;
  // more env variables...
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
  readonly hot: any;
  readonly glob: any;
}
