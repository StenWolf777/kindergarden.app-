// Dedicated, non-standard ports so the e2e suite never collides with (or
// silently attaches to) a real dev instance running on the usual 8000/4321.
module.exports = {
  BACKEND_PORT: 8099,
  FRONTEND_PORT: 4399,
};
