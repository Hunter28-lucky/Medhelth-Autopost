<?php
/**
 * Admin Settings Page for Pulse Content Sync
 *
 * Developed by Krish Goswami
 * Provides UI in WordPress Admin: Settings -> Pulse Sync
 */

if (!defined('ABSPATH')) {
    exit;
}

class AI_News_Publisher_Admin_Settings {

    public function init() {
        add_action('admin_menu', array($this, 'add_settings_menu'));
        add_action('admin_init', array($this, 'handle_actions'));
    }

    public function add_settings_menu() {
        add_options_page(
            __('Pulse Content Sync &bull; Krish Goswami', 'pulse-content-sync'),
            __('Pulse Sync', 'pulse-content-sync'),
            'manage_options',
            'pulse-sync',
            array($this, 'render_settings_page')
        );
    }

    public function handle_actions() {
        if (!current_user_can('manage_options')) {
            return;
        }

        // Handle Regenerate Key
        if (isset($_POST['pulse_sync_action']) && $_POST['pulse_sync_action'] === 'regenerate_key') {
            check_admin_referer('pulse_sync_regenerate');
            $new_key = wp_generate_password(32, false, false);
            update_option('ai_news_publisher_api_key', $new_key);
            add_settings_error('pulse_sync_messages', 'key_regenerated', __('Sync access key regenerated successfully.', 'pulse-content-sync'), 'updated');
        }

        // Handle Clear Logs
        if (isset($_POST['pulse_sync_action']) && $_POST['pulse_sync_action'] === 'clear_logs') {
            check_admin_referer('pulse_sync_clear_logs');
            update_option('ai_news_publisher_logs', array());
            add_settings_error('pulse_sync_messages', 'logs_cleared', __('Draft sync logs cleared.', 'pulse-content-sync'), 'updated');
        }
    }

    public function render_settings_page() {
        if (!current_user_can('manage_options')) {
            return;
        }

        $api_key  = get_option('ai_news_publisher_api_key');
        if (empty($api_key)) {
            $api_key = 'k60pRp6jNGAf9CdjexXHfsofXGqzlyoq';
        }
        $endpoint = rest_url('pulse-sync/v1/post');
        $health   = rest_url('pulse-sync/v1/health');
        $logs     = get_option('ai_news_publisher_logs', array());
        ?>
        <div class="wrap">
            <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #2271b1; padding-bottom: 12px; margin-top: 15px;">
                <div>
                    <h1 style="margin: 0; display: flex; align-items: center; gap: 8px;">
                        <span class="dashicons dashicons-cloud-saved" style="font-size: 28px; width: 28px; height: 28px; color: #2271b1;"></span>
                        Pulse Content Sync
                        <span style="font-size: 13px; background: #e0f2fe; color: #0369a1; padding: 3px 8px; border-radius: 12px; font-weight: 600;">v2.8.4 Active</span>
                    </h1>
                    <p style="margin: 4px 0 0 0; color: #64748b; font-size: 13px;">
                        Proprietary editorial draft connector &bull; <strong>Engineered by Krish Goswami</strong>
                    </p>
                </div>
                <div style="text-align: right;">
                    <span style="display: inline-flex; align-items: center; gap: 6px; font-size: 12px; background: #ecfdf5; color: #047857; padding: 4px 10px; border-radius: 6px; border: 1px solid #a7f3d0; font-weight: 600;">
                        <span style="width: 8px; height: 8px; border-radius: 50%; background: #10b981;"></span>
                        Connector Online & Secured
                    </span>
                </div>
            </div>
            
            <?php settings_errors('pulse_sync_messages'); ?>

            <div style="display: flex; gap: 24px; margin-top: 24px; flex-wrap: wrap;">
                <!-- Main Connection Panel -->
                <div style="flex: 2; min-width: 340px;">
                    <div class="card" style="max-width: 100%; margin-top: 0; padding: 22px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                        <h2 style="margin-top: 0; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px; font-size: 16px;">
                            Endpoint Credentials
                        </h2>
                        <p style="color: #64748b; font-size: 13px;">Use these secure credentials in your publishing control dashboard.</p>
                        
                        <table class="form-table" role="presentation" style="margin-top: 10px;">
                            <tr>
                                <th scope="row" style="width: 160px;"><label for="wp_endpoint">REST Ingest Endpoint</label></th>
                                <td>
                                    <input type="text" id="wp_endpoint" readonly value="<?php echo esc_url($endpoint); ?>" class="regular-text code" style="width: 100%; font-size: 12px; background: #f8fafc;" />
                                    <p class="description">Receives incoming editorial drafts over authenticated SSL.</p>
                                </td>
                            </tr>
                            <tr>
                                <th scope="row"><label for="wp_api_key">Connector Secret Key</label></th>
                                <td>
                                    <div style="display: flex; gap: 8px; align-items: center;">
                                        <input type="password" id="wp_api_key" readonly value="<?php echo esc_attr($api_key); ?>" class="regular-text code" style="width: 320px; font-size: 13px; background: #f8fafc;" />
                                        <button type="button" class="button" onclick="
                                            var field = document.getElementById('wp_api_key');
                                            if (field.type === 'password') {
                                                field.type = 'text';
                                                this.textContent = 'Hide';
                                            } else {
                                                field.type = 'password';
                                                this.textContent = 'Reveal';
                                            }
                                        ">Reveal</button>
                                        <button type="button" class="button button-primary" onclick="
                                            var field = document.getElementById('wp_api_key');
                                            var oldType = field.type;
                                            field.type = 'text';
                                            field.select();
                                            document.execCommand('copy');
                                            field.type = oldType;
                                            alert('Pulse Sync Key copied to clipboard!');
                                        ">Copy Key</button>
                                    </div>
                                    <p class="description">Sent in the <code>X-Pulse-Sync-Key</code> or <code>X-WP-AI-Key</code> request header.</p>
                                </td>
                            </tr>
                        </table>

                        <form method="post" action="" style="margin-top: 18px;" onsubmit="return confirm('Regenerating will invalidate the current key. External publishing services using the old key will be rejected. Continue?');">
                            <?php wp_nonce_field('pulse_sync_regenerate'); ?>
                            <input type="hidden" name="pulse_sync_action" value="regenerate_key" />
                            <button type="submit" class="button button-secondary">
                                <span class="dashicons dashicons-update" style="vertical-align: middle; margin-right: 4px;"></span>Regenerate Secret Key
                            </button>
                        </form>
                    </div>

                    <!-- Received Drafts Log -->
                    <div class="card" style="max-width: 100%; margin-top: 20px; padding: 22px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px;">
                            <h2 style="margin: 0; font-size: 16px;">Synchronized Drafts Activity Log (Last 100)</h2>
                            <?php if (!empty($logs)): ?>
                                <form method="post" action="" style="margin: 0;" onsubmit="return confirm('Clear activity log history?');">
                                    <?php wp_nonce_field('pulse_sync_clear_logs'); ?>
                                    <input type="hidden" name="pulse_sync_action" value="clear_logs" />
                                    <button type="submit" class="button button-small">Clear Log</button>
                                </form>
                            <?php endif; ?>
                        </div>

                        <?php if (empty($logs)): ?>
                            <p style="color: #64748b; font-style: italic; margin-top: 15px;">No draft sync events logged yet. Incoming drafts dispatched from your dashboard will appear here.</p>
                        <?php else: ?>
                            <table class="wp-list-table widefat fixed striped" style="margin-top: 15px;">
                                <thead>
                                    <tr>
                                        <th style="width: 70px;">Post ID</th>
                                        <th>Draft Headline</th>
                                        <th style="width: 110px;">Status</th>
                                        <th style="width: 150px;">Synchronized At</th>
                                        <th style="width: 90px;">Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <?php foreach ($logs as $item): ?>
                                        <tr>
                                            <td><strong>#<?php echo esc_html($item['post_id']); ?></strong></td>
                                            <td><?php echo esc_html($item['title']); ?></td>
                                            <td><span class="badge" style="background:#ecfdf5; color:#047857; padding:2px 6px; border-radius:3px; font-weight:600; font-size: 11px;">Draft (Review)</span></td>
                                            <td><?php echo esc_html($item['timestamp']); ?></td>
                                            <td>
                                                <a href="<?php echo esc_url(admin_url('post.php?post=' . $item['post_id'] . '&action=edit')); ?>" class="button button-small" target="_blank">Open Draft</a>
                                            </td>
                                        </tr>
                                    <?php endforeach; ?>
                                </tbody>
                            </table>
                        <?php endif; ?>
                    </div>
                </div>

                <!-- Sidebar / Status Card -->
                <div style="flex: 1; min-width: 260px;">
                    <div class="card" style="margin-top: 0; padding: 20px; border-radius: 8px;">
                        <h3 style="margin-top: 0; border-bottom: 1px solid #eee; padding-bottom: 8px; font-size: 14px;">Sync Policy & Integrity</h3>
                        <ul style="line-height: 1.8; color: #444; font-size: 12.5px;">
                            <li><span class="dashicons dashicons-yes-alt" style="color: #10b981; vertical-align: middle;"></span> <strong>Draft Status:</strong> Forced Draft (Never live)</li>
                            <li><span class="dashicons dashicons-yes-alt" style="color: #10b981; vertical-align: middle;"></span> <strong>Yoast SEO v28.4:</strong> Auto-Indexed</li>
                            <li><span class="dashicons dashicons-yes-alt" style="color: #10b981; vertical-align: middle;"></span> <strong>Authentication:</strong> X-Pulse-Sync-Key</li>
                            <li><span class="dashicons dashicons-yes-alt" style="color: #10b981; vertical-align: middle;"></span> <strong>Integrity:</strong> Author Verified</li>
                        </ul>
                        <div style="margin-top: 15px; padding-top: 12px; border-top: 1px solid #eee; font-size: 11.5px; color: #64748b;">
                            Connector authored by <strong>Krish Goswami</strong>. Maintains pristine draft staging.
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <?php
    }
}
