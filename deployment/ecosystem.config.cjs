/**
 * File: deployment/ecosystem.config.cjs
 * Purpose:
 *  - Run the pipeline.acm.is Next.js operator interface under PM2.
 *  - Keep the service isolated on VPS loopback port 3003.
 */

const deploymentRoot = "/home/hreidar/apps/acm-pipeline";
const applicationRoot = `${deploymentRoot}/current/Crystal-Workshop/ACM-Web-Pipeline`;

module.exports = {
  apps: [
    {
      name: "acm-pipeline",
      cwd: applicationRoot,
      script: "node_modules/next/dist/bin/next",
      args: "start --hostname 127.0.0.1 --port 3003",
      env: {
        NODE_ENV: "production",
        CONVERTER_ROOT: `${deploymentRoot}/current/Crystal-Workshop/pipeline-converter`,
        MESHY_ROOT: `${deploymentRoot}/current/Crystal-Workshop/meshy-pipeline`,
        IMAGE_PIPELINE_ROOT: `${deploymentRoot}/current/Crystal-Workshop/image-pipeline`,
      },
      autorestart: true,
      max_memory_restart: "750M",
      restart_delay: 3000,
      kill_timeout: 30000,
      time: true,
    },
  ],
};
