module.exports = {
  apps: [
    {
      name: "huangclaw-slack",
      cwd: __dirname,
      script: process.platform === "win32" ? "uv.cmd" : "uv",
      args: [
        "run",
        "uvicorn",
        "huangclaw.slack_app:api",
        "--host",
        "0.0.0.0",
        "--port",
        process.env.HUANGCLAW_PORT || "3010",
      ],
      interpreter: "none",
      watch: false,
      max_memory_restart: "800M",
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
  ],
};
