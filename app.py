import logging
from flask import Flask, jsonify
from config import validate_config
from database.mongodb import ping_db
from routes.ai_routes import ai_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Application factory — creates and configures the Flask app."""
    # Validate required environment variables before anything else
    validate_config()

    app = Flask(__name__)

    # Register blueprints
    app.register_blueprint(ai_bp)

    # Health endpoint — confirms Flask is up and MongoDB is reachable
    @app.route("/health", methods=["GET"])
    def health():
        try:
            ping_db()
            logger.info("Health check passed.")
            return jsonify({"status": "ok", "mongodb": "connected"}), 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({"status": "error", "mongodb": "unreachable"}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    logger.info("Starting Flask development server...")
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
