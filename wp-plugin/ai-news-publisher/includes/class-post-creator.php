<?php
/**
 * Post Creator Service for AI News Publisher
 *
 * Handles post creation, category/tag assignment, SEO metadata,
 * and editorial meta boxes for human reviewers.
 */

if (!defined('ABSPATH')) {
    exit;
}

class AI_News_Publisher_Post_Creator {

    public function __construct() {
        add_action('add_meta_boxes', array($this, 'register_source_meta_box'));
    }

    /**
     * Create a draft post from validated payload
     *
     * @param array $data
     * @return array|WP_Error
     */
    public function create_draft_post($data) {
        // Enforce post status as 'draft' at all times
        $post_status = 'draft';

        $title   = sanitize_text_field($data['title']);
        $content = wp_kses_post($data['body_html']);
        $excerpt = !empty($data['excerpt']) ? sanitize_textarea_field($data['excerpt']) : '';
        $slug    = !empty($data['slug']) ? sanitize_title($data['slug']) : sanitize_title($title);

        // Prepare post array
        $post_arr = array(
            'post_title'   => $title,
            'post_content' => $content,
            'post_excerpt' => $excerpt,
            'post_name'    => $slug,
            'post_status'  => $post_status,
            'post_type'    => 'post',
            'post_author'  => get_current_user_id() ?: 1,
        );

        // Handle Categories
        $cat_ids = array();
        if (!empty($data['categories']) && is_array($data['categories'])) {
            foreach ($data['categories'] as $cat_name) {
                $clean_cat = sanitize_text_field($cat_name);
                if (!empty($clean_cat)) {
                    $term = term_exists($clean_cat, 'category');
                    if ($term) {
                        $cat_ids[] = is_array($term) ? intval($term['term_id']) : intval($term);
                    } else {
                        if (!function_exists('wp_create_category')) {
                            require_once ABSPATH . 'wp-admin/includes/taxonomy.php';
                        }
                        $new_cat = wp_create_category($clean_cat);
                        if (!is_wp_error($new_cat) && $new_cat > 0) {
                            $cat_ids[] = intval($new_cat);
                        }
                    }
                }
            }
        }
        if (!empty($cat_ids)) {
            $post_arr['post_category'] = $cat_ids;
        }

        // Insert post
        $post_id = wp_insert_post($post_arr, true);

        if (is_wp_error($post_id)) {
            return $post_id;
        }

        // Handle Tags
        if (!empty($data['tags']) && is_array($data['tags'])) {
            $tags = array_map('sanitize_text_field', $data['tags']);
            wp_set_post_tags($post_id, $tags, false);
        }

        // Handle SEO Metadata (Yoast, RankMath, AIOSEO)
        $meta_title = !empty($data['meta_title']) ? sanitize_text_field($data['meta_title']) : $title;
        $meta_desc  = !empty($data['meta_description']) ? sanitize_textarea_field($data['meta_description']) : $excerpt;

        // Yoast SEO (v28.4 compatible) metadata
        $focus_kw = !empty($data['focus_keyphrase']) ? sanitize_text_field($data['focus_keyphrase']) : '';
        $yoast_seo_score = !empty($data['yoast_seo_score']) ? intval($data['yoast_seo_score']) : 90;
        $yoast_read_score = !empty($data['yoast_readability_score']) ? intval($data['yoast_readability_score']) : 90;

        if (!empty($focus_kw)) {
            update_post_meta($post_id, '_yoast_wpseo_focuskw', $focus_kw);
        }
        update_post_meta($post_id, '_yoast_wpseo_title', $meta_title);
        update_post_meta($post_id, '_yoast_wpseo_metadesc', $meta_desc);
        update_post_meta($post_id, '_yoast_wpseo_linkdex', (string)$yoast_seo_score);
        update_post_meta($post_id, '_yoast_wpseo_content_score', (string)$yoast_read_score);

        // Estimated reading time
        $word_count = str_word_count(strip_tags($content));
        $est_minutes = max(1, ceil($word_count / 200));
        update_post_meta($post_id, '_yoast_wpseo_estimated-reading-time-minutes', (string)$est_minutes);

        // Social Metadata
        update_post_meta($post_id, '_yoast_wpseo_opengraph-title', $meta_title);
        update_post_meta($post_id, '_yoast_wpseo_opengraph-description', $meta_desc);
        update_post_meta($post_id, '_yoast_wpseo_twitter-title', $meta_title);
        update_post_meta($post_id, '_yoast_wpseo_twitter-description', $meta_desc);

        // Synchronize Yoast Indexables database table if present
        $this->sync_yoast_indexables($post_id, $meta_title, $meta_desc, $focus_kw, $yoast_seo_score, $yoast_read_score, $est_minutes);

        // Rank Math SEO fields
        update_post_meta($post_id, 'rank_math_title', $meta_title);
        update_post_meta($post_id, 'rank_math_description', $meta_desc);

        // All in One SEO fields
        update_post_meta($post_id, '_aioseo_title', $meta_title);
        update_post_meta($post_id, '_aioseo_description', $meta_desc);

        // Store Research Sources and AI Publisher Meta
        if (!empty($data['sources_used'])) {
            update_post_meta($post_id, '_ai_publisher_sources', $data['sources_used']);
        }
        if (!empty($data['key_takeaways'])) {
            update_post_meta($post_id, '_ai_publisher_key_takeaways', $data['key_takeaways']);
        }
        if (!empty($data['disclaimer'])) {
            update_post_meta($post_id, '_ai_publisher_disclaimer', sanitize_textarea_field($data['disclaimer']));
        }
        if (!empty($data['run_id'])) {
            update_post_meta($post_id, '_ai_publisher_run_id', sanitize_text_field($data['run_id']));
        }
        update_post_meta($post_id, '_ai_publisher_generated_at', current_time('mysql'));

        // Handle Optional Featured Image Sideloading
        if (!empty($data['featured_image_url'])) {
            $this->sideload_featured_image($post_id, esc_url_raw($data['featured_image_url']), $title);
        }

        // Record incoming post in admin activity log
        $this->record_activity_log(array(
            'post_id'   => $post_id,
            'title'     => $title,
            'status'    => 'draft',
            'run_id'    => !empty($data['run_id']) ? sanitize_text_field($data['run_id']) : 'manual',
            'timestamp' => current_time('mysql'),
            'sources'   => !empty($data['sources_used']) ? count($data['sources_used']) : 0,
        ));

        return array(
            'post_id'   => $post_id,
            'status'    => 'draft',
            'title'     => $title,
            'edit_url'  => admin_url('post.php?post=' . $post_id . '&action=edit'),
            'preview_url' => get_preview_post_link($post_id),
            'message'   => 'Draft created successfully',
        );
    }

    /**
     * Download and attach featured image safely
     */
    private function sideload_featured_image($post_id, $image_url, $title) {
        if (!function_exists('media_sideload_image')) {
            require_once ABSPATH . 'wp-admin/includes/media.php';
            require_once ABSPATH . 'wp-admin/includes/file.php';
            require_once ABSPATH . 'wp-admin/includes/image.php';
        }

        $image_id = media_sideload_image($image_url, $post_id, $title, 'id');
        if (!is_wp_error($image_id)) {
            set_post_thumbnail($post_id, $image_id);
        }
    }

    /**
     * Synchronize with Yoast SEO Indexables database table if present
     */
    private function sync_yoast_indexables($post_id, $title, $description, $focus_kw, $seo_score, $read_score, $est_minutes) {
        global $wpdb;
        $table_name = $wpdb->prefix . 'yoast_indexable';

        // Check if yoast_indexable table exists
        if ($wpdb->get_var("SHOW TABLES LIKE '$table_name'") === $table_name) {
            $now = current_time('mysql');
            $existing = $wpdb->get_var($wpdb->prepare("SELECT id FROM $table_name WHERE object_id = %d AND object_type = 'post'", $post_id));

            $data = array(
                'object_id'                      => $post_id,
                'object_type'                    => 'post',
                'object_sub_type'                => 'post',
                'title'                          => $title,
                'description'                    => $description,
                'primary_focus_keyword'          => $focus_kw,
                'primary_focus_keyword_score'    => $seo_score,
                'readability_score'              => $read_score,
                'estimated_reading_time_minutes' => $est_minutes,
                'is_robots_noindex'              => 0,
                'updated_at'                     => $now,
            );

            if ($existing) {
                $wpdb->update($table_name, $data, array('id' => $existing));
            } else {
                $data['created_at'] = $now;
                $wpdb->insert($table_name, $data);
            }
        }
    }

    /**
     * Record activity in option log (keeps latest 100 entries)
     */
    private function record_activity_log($entry) {
        $logs = get_option('ai_news_publisher_logs', array());
        if (!is_array($logs)) {
            $logs = array();
        }
        array_unshift($logs, $entry);
        if (count($logs) > 100) {
            $logs = array_slice($logs, 0, 100);
        }
        update_option('ai_news_publisher_logs', $logs);
    }

    /**
     * Register meta box in Post edit screen for human editors
     */
    public function register_source_meta_box() {
        add_meta_box(
            'pulse_content_sync_meta_box',
            __('Pulse Content Sync: Editorial Citations & Sources', 'pulse-content-sync'),
            array($this, 'render_source_meta_box'),
            'post',
            'normal',
            'high'
        );
    }

    /**
     * Render the editorial meta box
     */
    public function render_source_meta_box($post) {
        $sources   = get_post_meta($post->ID, '_ai_publisher_sources', true);
        $run_id    = get_post_meta($post->ID, '_ai_publisher_run_id', true);
        $gen_at    = get_post_meta($post->ID, '_ai_publisher_generated_at', true);
        $takeaways = get_post_meta($post->ID, '_ai_publisher_key_takeaways', true);
        $disclaimer = get_post_meta($post->ID, '_ai_publisher_disclaimer', true);

        echo '<div style="font-size: 13px; line-height: 1.6;">';
        echo '<p style="margin-top:0; color: #1e293b;"><strong>Editorial Note:</strong> Synchronized via Pulse Content Sync (developed by Krish Goswami). Please review clinical citations and source references prior to publication.</p>';

        if ($run_id || $gen_at) {
            echo '<p style="color: #64748b; font-size: 12px; margin-bottom: 12px;">';
            if ($run_id) echo '<strong>Sync Batch:</strong> ' . esc_html($run_id) . ' &bull; ';
            if ($gen_at) echo '<strong>Synced:</strong> ' . esc_html($gen_at);
            echo '</p>';
        }

        if (!empty($sources) && is_array($sources)) {
            echo '<h4 style="margin: 10px 0 6px 0; color: #0f172a;">Referenced Citations & Sources (' . count($sources) . '):</h4>';
            echo '<ul style="margin: 0 0 16px 20px; list-style-type: disc;">';
            foreach ($sources as $source) {
                if (is_array($source)) {
                    $url   = !empty($source['url']) ? esc_url($source['url']) : '#';
                    $stitle = !empty($source['title']) ? esc_html($source['title']) : esc_html($url);
                    $domain = !empty($source['domain']) ? ' (' . esc_html($source['domain']) . ')' : '';
                    echo '<li><a href="' . $url . '" target="_blank" rel="noopener noreferrer"><strong>' . $stitle . '</strong></a>' . $domain . '</li>';
                } else {
                    $url = esc_url($source);
                    echo '<li><a href="' . $url . '" target="_blank" rel="noopener noreferrer">' . $url . '</a></li>';
                }
            }
            echo '</ul>';
        }

        if (!empty($takeaways)) {
            echo '<h4 style="margin: 10px 0 6px 0;">Key Takeaways Grounding:</h4>';
            if (is_array($takeaways)) {
                echo '<ul style="margin: 0 0 16px 20px; list-style-type: square;">';
                foreach ($takeaways as $t) {
                    echo '<li>' . esc_html($t) . '</li>';
                }
                echo '</ul>';
            } else {
                echo '<p style="background:#f8f9fa; padding:8px 12px; border-left:3px solid #0073aa;">' . esc_html($takeaways) . '</p>';
            }
        }

        if (!empty($disclaimer)) {
            echo '<p style="background: #fff8e5; border-left: 3px solid #ffba00; padding: 8px 12px; margin-top: 12px;"><strong>Disclaimer Appended:</strong> ' . esc_html($disclaimer) . '</p>';
        }

        echo '</div>';
    }
}
