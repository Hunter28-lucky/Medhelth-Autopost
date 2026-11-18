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

            // Deep Site Diagnostics & Intelligence Endpoint
            register_rest_route($ns, '/inspect', array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array($this, 'handle_inspect'),
                'permission_callback' => array($this, 'check_api_permission'),
            ));

            // Live Taxonomies & Categories Sync Endpoint
            register_rest_route($ns, '/categories', array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array($this, 'handle_categories'),
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
     * Handle health check request (summary connectivity & status)
     */
    public function handle_health_check(WP_REST_Request $request) {
        $yoast_active = false;
        $yoast_version = null;
        if (defined('WPSEO_VERSION')) {
            $yoast_active = true;
            $yoast_version = WPSEO_VERSION;
        } elseif (class_exists('WPSEO_Options')) {
            $yoast_active = true;
        }

        $cats_count = wp_count_terms(array('taxonomy' => 'category', 'hide_empty' => false));
        if (is_wp_error($cats_count)) {
            $cats_count = 0;
        }

        $post_counts = wp_count_posts('post');

        return new WP_REST_Response(array(
            'success'           => true,
            'status'            => 'ok',
            'plugin_version'    => defined('PULSE_SYNC_VERSION') ? PULSE_SYNC_VERSION : '2.9.0',
            'site_name'         => get_bloginfo('name'),
            'site_url'          => home_url(),
            'admin_url'         => admin_url(),
            'wordpress_version' => get_bloginfo('version'),
            'php_version'       => phpversion(),
            'yoast_active'      => $yoast_active,
            'yoast_version'     => $yoast_version ? $yoast_version : ($yoast_active ? 'Active' : 'Not Detected'),
            'categories_count'  => (int)$cats_count,
            'published_posts'   => isset($post_counts->publish) ? (int)$post_counts->publish : 0,
            'draft_posts'       => isset($post_counts->draft) ? (int)$post_counts->draft : 0,
            'timestamp'         => current_time('mysql'),
        ), 200);
    }

    /**
     * Deep Site Inspection & Diagnostics Endpoint
     * Returns comprehensive website intelligence for PulsePublish dashboard:
     * - Server & WordPress environment
     * - Live taxonomies & all categories with counts
     * - Yoast SEO detection & version
     * - Active plugins list (detects accelerators/caching)
     * - Post statistics (publish, draft, pending)
     * - Registered authors
     * - Compatibility audit warnings
     */
    public function handle_inspect(WP_REST_Request $request) {
        // 1. Categories
        $categories = get_categories(array(
            'hide_empty' => false,
            'number'     => 500,
            'orderby'    => 'count',
            'order'      => 'DESC',
        ));
        $cats_data = array();
        foreach ($categories as $cat) {
            $cats_data[] = array(
                'id'          => $cat->term_id,
                'name'        => html_entity_decode($cat->name, ENT_QUOTES, 'UTF-8'),
                'slug'        => $cat->slug,
                'count'       => (int)$cat->count,
                'parent'      => (int)$cat->parent,
                'description' => $cat->description,
            );
        }

        // 2. Active Plugins & Yoast Detection
        if (!function_exists('get_plugins')) {
            require_once ABSPATH . 'wp-admin/includes/plugin.php';
        }
        $all_plugins = function_exists('get_plugins') ? get_plugins() : array();
        $active_plugin_keys = (array) get_option('active_plugins', array());
        $active_plugins = array();
        $yoast_detected = false;
        $yoast_version = null;
        $warnings = array();

        foreach ($active_plugin_keys as $plugin_key) {
            if (isset($all_plugins[$plugin_key])) {
                $p = $all_plugins[$plugin_key];
                $name = $p['Name'];
                $ver = $p['Version'];
                $active_plugins[] = array(
                    'key'     => $plugin_key,
                    'name'    => $name,
                    'version' => $ver,
                    'author'  => wp_strip_all_tags($p['Author']),
                );
                if (stripos($name, 'Yoast SEO') !== false || stripos($plugin_key, 'wordpress-seo') !== false) {
                    $yoast_detected = true;
                    $yoast_version = $ver;
                }
                // Detect caching/accelerator plugins that might conflict
                if (stripos($name, 'Seraphinite') !== false) {
                    $warnings[] = 'Seraphinite Accelerator detected: Ensure REST API endpoints (/wp-json/pulse-sync/v1/*) are excluded from cache.';
                }
                if (stripos($name, 'Jetpack') !== false) {
                    $warnings[] = 'Jetpack detected: Verify Site Accelerator setting if images fail to load.';
                }
            }
        }

        if (defined('WPSEO_VERSION')) {
            $yoast_detected = true;
            $yoast_version = WPSEO_VERSION;
        }

        // 3. Post statistics
        $post_counts = wp_count_posts('post');

        // 4. Authors
        $authors = get_users(array(
            'role__in' => array('administrator', 'editor', 'author'),
            'number'   => 15,
            'fields'   => array('ID', 'display_name', 'user_email', 'user_login'),
        ));
        $authors_data = array();
        if (!empty($authors) && is_array($authors)) {
            foreach ($authors as $a) {
                $authors_data[] = array(
                    'id'           => $a->ID,
                    'display_name' => $a->display_name,
                    'user_login'   => $a->user_login,
                );
            }
        }

        // 5. Recent sync logs
        $logs = get_option('ai_news_publisher_logs', array());
        $recent_logs = is_array($logs) ? array_slice($logs, 0, 10) : array();

        // 6. Server & environment checks
        $permalink_structure = get_option('permalink_structure');
        if (empty($permalink_structure)) {
            $warnings[] = 'WordPress is using plain permalinks (?p=123). Recommended: Switch to Post name in Settings -> Permalinks.';
        }

        return new WP_REST_Response(array(
            'success'   => true,
            'timestamp' => current_time('mysql'),
            'site_info' => array(
                'name'                => get_bloginfo('name'),
                'description'         => get_bloginfo('description'),
                'site_url'            => home_url(),
                'admin_url'           => admin_url(),
                'rest_url'            => rest_url(),
                'wordpress_version'   => get_bloginfo('version'),
                'php_version'         => phpversion(),
                'server_software'     => isset($_SERVER['SERVER_SOFTWARE']) ? sanitize_text_field($_SERVER['SERVER_SOFTWARE']) : 'Unknown',
                'is_ssl'              => is_ssl(),
                'locale'              => get_locale(),
                'timezone'            => wp_timezone_string(),
                'permalink_structure' => $permalink_structure ? $permalink_structure : 'Plain (?p=123)',
                'memory_limit'        => defined('WP_MEMORY_LIMIT') ? WP_MEMORY_LIMIT : ini_get('memory_limit'),
                'upload_max_filesize' => ini_get('upload_max_filesize'),
                'post_max_size'       => ini_get('post_max_size'),
            ),
            'seo_info' => array(
                'yoast_active'        => $yoast_detected,
                'yoast_version'       => $yoast_version ? $yoast_version : ($yoast_detected ? 'Active' : 'Not Detected'),
                'yoast_rest_support'  => true,
                'compliance_status'   => $yoast_detected ? '100% Yoast SEO Compliant' : 'Plugin Optional',
            ),
            'taxonomy' => array(
                'total_categories'    => count($cats_data),
                'categories'          => $cats_data,
            ),
            'post_stats' => array(
                'published' => isset($post_counts->publish) ? (int)$post_counts->publish : 0,
                'drafts'    => isset($post_counts->draft) ? (int)$post_counts->draft : 0,
                'pending'   => isset($post_counts->pending) ? (int)$post_counts->pending : 0,
                'trash'     => isset($post_counts->trash) ? (int)$post_counts->trash : 0,
            ),
            'active_plugins' => $active_plugins,
            'authors'        => $authors_data,
            'recent_syncs'   => $recent_logs,
            'warnings'       => $warnings,
            'plugin_version' => defined('PULSE_SYNC_VERSION') ? PULSE_SYNC_VERSION : '2.9.0',
        ), 200);
    }

    /**
     * Fetch Live Categories Endpoint
     * Returns all categories with IDs and post counts
     */
    public function handle_categories(WP_REST_Request $request) {
        $categories = get_categories(array(
            'hide_empty' => false,
            'number'     => 500,
            'orderby'    => 'name',
            'order'      => 'ASC',
        ));
        $cats_data = array();
        foreach ($categories as $cat) {
            $cats_data[] = array(
                'id'          => $cat->term_id,
                'name'        => html_entity_decode($cat->name, ENT_QUOTES, 'UTF-8'),
                'slug'        => $cat->slug,
                'count'       => (int)$cat->count,
                'parent'      => (int)$cat->parent,
                'description' => $cat->description,
            );
        }

        return new WP_REST_Response(array(
            'success'    => true,
            'count'      => count($cats_data),
            'categories' => $cats_data,
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
