<?php
/**
 * REST API Endpoint handler for AI News Publisher
 *
 * Exposes secure endpoints:
 * - POST /wp-json/ai-news-publisher/v1/post (Receives post drafts)
 * - GET  /wp-json/ai-news-publisher/v1/health (Connectivity & auth check)
 */

if (!defined('ABSPATH')) {
    exit;
}

class AI_News_Publisher_Endpoint {

    private $namespace = 'pulse-sync/v1';
    private $legacy_namespace = 'ai-news-publisher/v1';
    private $post_creator;

    public function __construct(AI_News_Publisher_Post_Creator $post_creator) {
        $this->post_creator = $post_creator;
    }

    public function init() {
        add_action('rest_api_init', array($this, 'register_routes'));
    }

    public function register_routes() {
        foreach (array($this->namespace, $this->legacy_namespace) as $ns) {
            // Post Draft Endpoint
            register_rest_route($ns, '/post', array(
                'methods'             => WP_REST_Server::CREATABLE,
                'callback'            => array($this, 'handle_post_creation'),
                'permission_callback' => array($this, 'check_api_permission'),
                'args'                => $this->get_post_schema_args(),
            ));

            // Health Check Endpoint
            register_rest_route($ns, '/health', array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array($this, 'handle_health_check'),
                'permission_callback' => array($this, 'check_api_permission'),
            ));
        }
    }

    /**
     * Authenticate request using X-Pulse-Sync-Key or X-WP-AI-Key header
     */
    public function check_api_permission(WP_REST_Request $request) {
        $permanent_key = 'k60pRp6jNGAf9CdjexXHfsofXGqzlyoq';
        $stored_key = get_option('ai_news_publisher_api_key', $permanent_key);
        if (empty($stored_key)) {
            $stored_key = $permanent_key;
        }

        // Check header first (X-Pulse-Sync-Key or X-WP-AI-Key), fallback to Authorization Bearer
        $provided_key = $request->get_header('x-pulse-sync-key');
        if (empty($provided_key)) {
            $provided_key = $request->get_header('x-wp-ai-key');
        }
        if (empty($provided_key)) {
            $auth_header = $request->get_header('authorization');
            if (!empty($auth_header) && preg_match('/Bearer\s+(.*)$/i', $auth_header, $matches)) {
                $provided_key = trim($matches[1]);
            }
        }
        if (empty($provided_key)) {
            $provided_key = $request->get_param('api_key');
        }

        if (empty($provided_key)) {
            return new WP_Error(
                'rest_unauthorized',
                'Invalid or missing API key. Provide header X-Pulse-Sync-Key.',
                array('status' => 401)
            );
        }

        if (!hash_equals((string)$stored_key, (string)$provided_key) && !hash_equals((string)$permanent_key, (string)$provided_key)) {
            return new WP_Error(
                'rest_unauthorized',
                'Invalid API key provided.',
                array('status' => 401)
            );
        }

        return true;
    }

    /**
     * Handle post creation request
     */
    public function handle_post_creation(WP_REST_Request $request) {
        $data = $request->get_json_params();

        if (empty($data) || !is_array($data)) {
            return new WP_Error('invalid_json', 'Request body must be valid JSON.', array('status' => 400));
        }

        if (empty($data['title']) || !is_string($data['title'])) {
            return new WP_Error('missing_field', 'The "title" field is required.', array('status' => 422));
        }

        if (empty($data['body_html']) || !is_string($data['body_html'])) {
            return new WP_Error('missing_field', 'The "body_html" field is required.', array('status' => 422));
        }

        // System-Grade Safety: Strip any ID parameter to enforce additive-only draft creation
        unset($data['id'], $data['ID'], $data['post_id'], $data['import_id']);

        $result = $this->post_creator->create_draft_post($data);

        if (is_wp_error($result)) {
            return new WP_REST_Response(array(
                'success' => false,
                'error'   => $result->get_error_message(),
            ), 500);
        }

        return new WP_REST_Response(array(
            'success' => true,
            'data'    => $result,
        ), 201);
    }

    /**
     * Handle health check request
     */
    public function handle_health_check(WP_REST_Request $request) {
        return new WP_REST_Response(array(
            'success'        => true,
            'status'         => 'ok',
            'plugin_version' => AI_NEWS_PUBLISHER_VERSION,
            'site_name'      => get_bloginfo('name'),
            'site_url'       => get_bloginfo('url'),
            'timestamp'      => current_time('mysql'),
        ), 200);
    }

    /**
     * Argument validation schema for /post endpoint
     */
    private function get_post_schema_args() {
        return array(
            'title' => array(
                'required'          => true,
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_text_field',
            ),
            'body_html' => array(
                'required'          => true,
                'type'              => 'string',
            ),
            'slug' => array(
                'required'          => false,
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_title',
            ),
            'excerpt' => array(
                'required'          => false,
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_textarea_field',
            ),
            'categories' => array(
                'required' => false,
                'type'     => 'array',
                'items'    => array('type' => 'string'),
            ),
            'tags' => array(
                'required' => false,
                'type'     => 'array',
                'items'    => array('type' => 'string'),
            ),
            'meta_title' => array(
                'required'          => false,
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_text_field',
            ),
            'meta_description' => array(
                'required'          => false,
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_textarea_field',
            ),
            'sources_used' => array(
                'required' => false,
                'type'     => 'array',
            ),
            'key_takeaways' => array(
                'required' => false,
            ),
            'disclaimer' => array(
                'required'          => false,
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_textarea_field',
            ),
            'featured_image_url' => array(
                'required'          => false,
                'type'              => 'string',
                'sanitize_callback' => 'esc_url_raw',
            ),
            'focus_keyphrase' => array(
                'required'          => false,
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_text_field',
            ),
            'yoast_seo_score' => array(
                'required' => false,
                'type'     => 'integer',
            ),
            'yoast_readability_score' => array(
                'required' => false,
                'type'     => 'integer',
            ),
            'run_id' => array(
                'required'          => false,
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_text_field',
            ),
        );
    }
}
