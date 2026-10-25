import { defineConfig, globalIgnores } from 'eslint/config';
import nextVitals from 'eslint-config-next/core-web-vitals';
import nextTs from 'eslint-config-next/typescript';

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores(['.next/**', 'out/**', 'build/**', 'next-env.d.ts']),
  {
    rules: {
      // Каталог отдаёт чужие URL картинок. next/image пишет кэш на диск — это запрещено.
      '@next/next/no-img-element': 'off',
    },
  },
]);

export default eslintConfig;
