const { defineConfig } = require('@playwright/test');
const root = require('path').resolve(__dirname, '..');
module.exports = defineConfig({ testDir: `${__dirname}/e2e`, testMatch: ['import-workspace.spec.cjs', 'import-file-picker.spec.cjs'], workers: 1, retries: 0,
 timeout: 180000, expect: { timeout: 18000 }, reporter: 'list', outputDir: `${process.env.IMPORT_WORKSPACE_OUTPUT}/ui-results-${process.env.IMPORT_RUN}`,
 use: { baseURL: process.env.E2E_BASE_URL, actionTimeout: 15000, screenshot: 'only-on-failure', trace: 'retain-on-failure' },
 webServer: [
 {command: `"${process.env.E2E_PYTHON}" frontend/e2e/serve-isolated.py`,cwd:root,url:`${process.env.E2E_API_BASE_URL}/health/`,reuseExistingServer:false,timeout:120000},
 {command:`node node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${process.env.E2E_FRONTEND_PORT} --strictPort`,cwd:`${root}/frontend`,url:process.env.E2E_BASE_URL,reuseExistingServer:false,timeout:120000}]
});
