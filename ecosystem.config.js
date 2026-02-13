module.exports = {
  apps: [
    {
      name: "rooting-future",
      script: "./venv/bin/waitress-serve",
      cwd: "/home/ubuntu/rooting_future",
      args: "--listen=*:5000 --threads=12 --channel-timeout=120 app:app",
      interpreter: "none",
      env: {
        NODE_ENV: "production",
      },
    },
  ],
};
