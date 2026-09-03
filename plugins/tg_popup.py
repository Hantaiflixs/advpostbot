# plugins/push_notification.py
import __main__

# --- ⚙️ কনফিগারেশন ---
# আপনার দেওয়া OneSignal App ID এখানে সেট করা হয়েছে
ONESIGNAL_APP_ID = "d8b008a1-623d-495d-b10d-8def7460f2ea" 

def get_push_notification_ui():
    return f"""
    <!-- OneSignal SDK - আপনার দেওয়া কোড -->
    <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
    <script>
      window.OneSignalDeferred = window.OneSignalDeferred || [];
      OneSignalDeferred.push(async function(OneSignal) {{
        await OneSignal.init({{
          appId: "{ONESIGNAL_APP_ID}",
        }});
      }});
    </script>

    <style>
        /* 🔔 পুশ নোটিফিকেশন বার ডিজাইন (চ্যাপ্টা ও নিচে) */
        #push-notice-bar {{
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background: rgba(10, 12, 16, 0.98);
            backdrop-filter: blur(15px);
            border-top: 2px solid #0088cc;
            padding: 10px 20px;
            display: none; /* শুরুতে হাইড থাকবে */
            align-items: center;
            justify-content: center;
            z-index: 9999999;
            box-shadow: 0 -10px 30px rgba(0, 0, 0, 0.8);
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }}

        .push-container {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            max-width: 1000px;
            width: 100%;
            gap: 15px;
        }}

        .push-content-text {{
            color: #ffffff;
            font-size: 14px;
            font-weight: 500;
            display: flex;
            align-items: center;
        }}

        .push-content-text b {{
            color: #0088cc;
            margin-right: 8px;
            font-size: 18px;
        }}

        .push-action-btns {{
            display: flex;
            gap: 12px;
            flex-shrink: 0;
        }}

        .btn-push-allow {{
            background: #0088cc;
            color: #fff;
            border: none;
            padding: 8px 20px;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
            font-size: 13px;
            transition: 0.3s;
            box-shadow: 0 4px 10px rgba(0, 136, 204, 0.3);
        }}

        .btn-push-deny {{
            background: rgba(255,255,255,0.05);
            color: #bbb;
            border: 1px solid #444;
            padding: 8px 18px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: 0.3s;
        }}

        .btn-push-allow:hover {{ background: #00aaff; transform: translateY(-2px); }}
        .btn-push-deny:hover {{ color: #fff; background: rgba(255,255,255,0.1); }}

        /* মোবাইল স্ক্রিনের জন্য রেসপন্সিভ */
        @media (max-width: 768px) {{
            #push-notice-bar {{ padding: 15px; }}
            .push-container {{ flex-direction: column; text-align: center; }}
            .push-content-text {{ margin-bottom: 5px; font-size: 13px; }}
            .btn-push-allow, .btn-push-deny {{ padding: 10px 15px; flex: 1; }}
            .push-action-btns {{ width: 100%; }}
        }}

        /* অ্যানিমেশন */
        @keyframes slideInUp {{
            from {{ transform: translateY(100%); }}
            to {{ transform: translateY(0); }}
        }}
        .animate-up {{ animation: slideInUp 0.6s cubic-bezier(0.23, 1, 0.32, 1); }}
    </style>

    <div id="push-notice-bar" class="animate-up">
        <div class="push-container">
            <div class="push-content-text">
                <b>🔔</b> নতুন মুভি বা সিরিজের আপডেট সবার আগে পেতে নোটিফিকেশন অ্যালাউ করুন!
            </div>
            <div class="push-action-btns">
                <button class="btn-push-deny" onclick="handlePushAction('deny')">পরে দেখবো</button>
                <button class="btn-push-allow" onclick="handlePushAction('allow')">হ্যাঁ, অ্যালাউ করুন</button>
            </div>
        </div>
    </div>

    <script>
        function checkNotificationStatus() {{
            OneSignalDeferred.push(function(OneSignal) {{
                // ইউজার যদি অলরেডি সাবস্ক্রাইবড না থাকে, তবেই বার দেখাবে
                if (!OneSignal.Notifications.permission) {{
                    setTimeout(() => {{
                        if (!sessionStorage.getItem('push_dismissed')) {{
                            document.getElementById('push-notice-bar').style.display = 'flex';
                        }}
                    }}, 3000); // ৩ সেকেন্ড পর লোড হবে
                }}
            }});
        }}

        async def handlePushAction(action) {{
            if (action === 'allow') {{
                OneSignalDeferred.push(async function(OneSignal) {{
                    await OneSignal.Notifications.requestPermission();
                }});
            }} else {{
                // সেশনের জন্য হাইড করে রাখা
                sessionStorage.setItem('push_dismissed', 'true');
            }}
            document.getElementById('push-notice-bar').style.display = 'none';
        }}

        // পেজ রেডি হলে রান করবে
        window.onload = checkNotificationStatus;
    </script>
    """

# ==========================================================
# 🔥 MONKEY PATCH: HTML GENERATOR
# ==========================================================

original_html_func = __main__.generate_html_code

def push_bar_injector(data, links, user_ads, owner_ads, share):
    html = original_html_func(data, links, user_ads, owner_ads, share)
    push_ui = get_push_notification_ui()
    return html + push_ui

# মেইন জেনারেটর রিপ্লেস করা
__main__.generate_html_code = push_bar_injector

async def register(bot):
    print("🚀 CineZone Web-Push Bar (Flat UI) Plugin Ready!")

print("✅ Plugin Updated Successfully with OneSignal ID: d8b008a1...")
