<?php
/**
 * Plugin Name:       Pulse Content Sync
 * Plugin URI:        https://krishgoswami.dev/pulse-sync
 * Description:       High-performance editorial sync and draft connector. Developed by Krish Goswami.
 * Version:           2.8.4
 * Requires at least: 5.8
 * Requires PHP:      7.4
 * Author:            Krish Goswami
 * Author URI:        https://krishgoswami.dev
 * Text Domain:       pulse-content-sync
 * License:           GPL v2 or later
 */

if (!defined('ABSPATH')) {
    exit;
}

define('PULSE_SYNC_VERSION', '2.8.4');
define('PULSE_SYNC_PATH', plugin_dir_path(__FILE__));
define('PULSE_SYNC_URL', plugin_dir_url(__FILE__));

// Backward compatibility defines
define('AI_NEWS_PUBLISHER_VERSION', PULSE_SYNC_VERSION);
define('AI_NEWS_PUBLISHER_PATH', PULSE_SYNC_PATH);
define('AI_NEWS_PUBLISHER_URL', PULSE_SYNC_URL);

// Autoload components
require_once PULSE_SYNC_PATH . 'includes/class-post-creator.php';
require_once PULSE_SYNC_PATH . 'includes/class-api-endpoint.php';
require_once PULSE_SYNC_PATH . 'includes/class-admin-settings.php';

/**
 * Plugin activation hook: initialize secure connector options
 */
function pulse_content_sync_activate() {
    if (!get_option('ai_news_publisher_api_key')) {
        $key = wp_generate_password(32, false, false);
        update_option('ai_news_publisher_api_key', $key);
    }

    if (!get_option('ai_news_publisher_default_status')) {
        update_option('ai_news_publisher_default_status', 'draft');
    }

    if (!get_option('ai_news_publisher_logs')) {
        update_option('ai_news_publisher_logs', array());
    }
}
register_activation_hook(__FILE__, 'pulse_content_sync_activate');

/**
 * Initialize Pulse Content Sync services
 */
function pulse_content_sync_init() {
    $post_creator = new AI_News_Publisher_Post_Creator();
    $api_endpoint = new AI_News_Publisher_Endpoint($post_creator);
    $api_endpoint->init();

    if (is_admin()) {
        $admin_settings = new AI_News_Publisher_Admin_Settings();
        $admin_settings->init();
    }
}
add_action('plugins_loaded', 'pulse_content_sync_init');

/**
 * Bypass maintenance mode plugins (such as Minimal Coming Soon) for legitimate REST API requests
 */
function pulse_content_sync_bypass_maintenance() {
    $is_pulse_request = false;

    // Check request URI for pulse-sync, ai-news-publisher, or wp-json endpoints
    if (!empty($_SERVER['REQUEST_URI'])) {
        $uri = $_SERVER['REQUEST_URI'];
        if (strpos($uri, 'pulse-sync') !== false || strpos($uri, 'ai-news-publisher') !== false || strpos($uri, 'wp-json') !== false) {
            $is_pulse_request = true;
        }
    }

    // Check auth headers
    if (!empty($_SERVER['HTTP_X_PULSE_SYNC_KEY']) || !empty($_SERVER['HTTP_X_WP_AI_KEY'])) {
        $is_pulse_request = true;
    }

    if ($is_pulse_request) {
        // Unhook Minimal Coming Soon & Maintenance Mode hook (csmm_plugin_init is hooked at init priority 10)
        remove_action('init', 'csmm_plugin_init');
    }
}
// Run at priority 1 on init, well before csmm_plugin_init at priority 10
add_action('init', 'pulse_content_sync_bypass_maintenance', 1);

/**
 * Add settings action link to plugins list
 */
function pulse_content_sync_settings_link($links) {
    $settings_link = '<a href="' . admin_url('options-general.php?page=pulse-sync') . '">' . __('Settings', 'pulse-content-sync') . '</a>';
    array_unshift($links, $settings_link);
    return $links;
}
add_filter('plugin_action_links_' . plugin_basename(__FILE__), 'pulse_content_sync_settings_link');
