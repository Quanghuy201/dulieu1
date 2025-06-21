import multiprocessing
import time
import json
import os
import string
from datetime import datetime
from collections import defaultdict
from zlapi import ZaloAPI, ThreadType, Message
from zlapi.models import Mention


class Logger:
    @staticmethod
    def log(msg, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {msg}")

    @staticmethod
    def error(msg):
        Logger.log(msg, "ERROR")


class Bot(ZaloAPI):
    def __init__(self, imei, session_cookies):
        super().__init__("dummy_key", "dummy_secret", imei, session_cookies)

    def fetchGroupInfo(self):
        try:
            all_groups = self.fetchAllGroups()
            group_list = []
            for group_id, _ in all_groups.gridVerMap.items():
                group_info = super().fetchGroupInfo(group_id)
                group_name = group_info.gridInfoMap[group_id]["name"]
                group_list.append({'id': group_id, 'name': group_name})
            return group_list
        except Exception as e:
            print(f"Lỗi khi lấy danh sách nhóm: {e}")
            return []

    def display_group_menu(self):
        groups = self.fetchGroupInfo()
        if not groups:
            print("Không tìm thấy nhóm nào.")
            return None
        grouped = defaultdict(list)
        for group in groups:
            first_char = group['name'][0].upper()
            if first_char not in string.ascii_uppercase:
                first_char = '#'
            grouped[first_char].append(group)
        print("\nDanh sách các nhóm:")
        index_map = {}
        idx = 1
        for letter in sorted(grouped.keys()):
            print(f"\nNhóm {letter}:")
            for group in grouped[letter]:
                print(f"{idx}. {group['name']} (ID: {group['id']})")
                index_map[idx] = group['id']
                idx += 1
        return index_map

    def select_group(self):
        index_map = self.display_group_menu()
        if not index_map:
            return None
        while True:
            try:
                choice = int(input("Nhập số thứ tự của nhóm: ").strip())
                if choice in index_map:
                    return index_map[choice]
                print("Số không hợp lệ.")
            except ValueError:
                print("Vui lòng nhập số hợp lệ.")


def read_file_content(filename):
    try:
        if not os.path.exists(filename):
            Logger.error(f"File không tồn tại: {filename}")
            return None
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                Logger.error("File trống.")
                return None
            return content
    except Exception as e:
        Logger.error(f"Lỗi đọc file: {str(e)}")
        return None


def validate_cookie(cookie_str):
    try:
        cookie = json.loads(cookie_str)
        if not isinstance(cookie, dict):
            raise ValueError("Cookie không đúng định dạng JSON object.")
        return cookie
    except json.JSONDecodeError:
        Logger.error("Cookie không hợp lệ (không phải JSON).")
    except Exception as e:
        Logger.error(f"Lỗi cookie: {str(e)}")
    return None


def start_bot_worker(imei, session_cookies, message_text, delay, thread_id):
    bot = Bot(imei, session_cookies)
    thread_type = ThreadType.GROUP
    mention = Mention("-1", offset=0, length=len(message_text))
    while True:
        try:
            if len(message_text) > 1000:
                bot.send(Message(text=message_text[:1000], mention=mention), thread_id, thread_type)
            else:
                bot.send(Message(text=message_text, mention=mention), thread_id, thread_type)
            Logger.log(f"✅ [{imei[:5]}] Đã gửi thành công")
        except Exception as e:
            Logger.error(f"❌ [{imei[:5]}] Lỗi gửi tin: {str(e)}")
        time.sleep(delay)


def get_account_info(index, is_last=False):
    print(f"\n🔹 Nhập thông tin cho tài khoản {index + 1} 🔹")
    imei = input("📱 Nhập IMEI: ").strip()
    while True:
        cookie_str = input("🍪 Nhập Cookie: ").strip()
        cookie = validate_cookie(cookie_str)
        if cookie:
            break
    bot = Bot(imei, cookie)
    thread_id = bot.select_group()
    if not thread_id:
        Logger.error("Không chọn được nhóm.")
        return None
    if not is_last:
        print("👉 Tài khoản này đã được lưu. Tiếp tục acc tiếp theo...\n")
    return (imei, cookie, thread_id)


def start_all_bots():
    print("🔹 Tool gửi nội dung từ file.txt bằng nhiều Zalo account 🔹")
    while True:
        try:
            num_accounts = int(input("👉 Nhập số lượng tài khoản muốn chạy (1-10): ").strip())
            if 1 <= num_accounts <= 10:
                break
            print("Số lượng phải từ 1 đến 10.")
        except ValueError:
            print("Vui lòng nhập số nguyên.")

    accounts = []
    for i in range(num_accounts):
        acc = get_account_info(i, is_last=(i == num_accounts - 1))
        if acc:
            accounts.append(acc)

    if not accounts:
        Logger.error("Không có tài khoản hợp lệ nào.")
        return

    while True:
        file_txt = input("📂 Nhập tên file .txt chứa nội dung spam: ").strip()
        message_text = read_file_content(file_txt)
        if message_text:
            break

    while True:
        try:
            delay = int(input("⏳ Nhập delay giữa các lần gửi (giây): ").strip())
            if delay >= 1:
                break
            print("Delay tối thiểu là 1 giây.")
        except ValueError:
            print("Vui lòng nhập số.")

    Logger.log("🎯 Bắt đầu gửi tin nhắn...")
    processes = []
    for imei, cookie, thread_id in accounts:
        p = multiprocessing.Process(target=start_bot_worker, args=(imei, cookie, message_text, delay, thread_id))
        processes.append(p)
        p.start()

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        Logger.log("Dừng tất cả bot...")
        for p in processes:
            p.terminate()
        Logger.log("Đã dừng.")


if __name__ == "__main__":
    start_all_bots()