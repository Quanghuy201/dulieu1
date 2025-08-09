import threading
import time
import os
import json
from collections import defaultdict
from zlapi import ZaloAPI, ThreadType, Message
from zlapi.models import Mention, MultiMsgStyle, MessageStyle
from config import API_KEY, SECRET_KEY

reset_color = "\033[0m"
do = "\033[1;31m"
xanh_la = "\033[1;32m"
vang = "\033[1;33m"
xanh_duong = "\033[1;34m"
tim = "\033[1;35m"
xanh_nhat = "\033[1;36m"

def validate_cookie(cookie_str):
    try:
        cookie = json.loads(cookie_str)
        if not isinstance(cookie, dict):
            raise ValueError()
        return cookie
    except:
        print(f"{do}❌ Cookie không hợp lệ.{reset_color}")
        return None

class Bot(ZaloAPI):
    def __init__(self, api_key, secret_key, imei=None, session_cookies=None):
        super().__init__(api_key, secret_key, imei, session_cookies)
        self.imei = imei
        self.group_name = "?"
        self.running = False
        self.use_mention = False
        self.use_tagall_style = False
        self.file_content = ""

    def fetch_group_info(self):
        try:
            all_groups = self.fetchAllGroups()
            group_list = []
            for group_id, _ in all_groups.gridVerMap.items():
                group_info = super().fetchGroupInfo(group_id)
                group_name = group_info.gridInfoMap[group_id]["name"]
                group_list.append({'id': group_id, 'name': group_name})
            return group_list
        except Exception as e:
            print(f"{do}Lỗi khi lấy danh sách nhóm: {e}{reset_color}")
            return []

    def display_group_menu_grouped(self, groups):
        if not groups:
            print(f"{do}Không tìm thấy nhóm nào.{reset_color}")
            return None
        grouped = defaultdict(list)
        for group in groups:
            first_letter = group['name'][0].lower()
            grouped[first_letter].append(group)
        flat_list = []
        count = 1
        for letter in sorted(grouped.keys()):
            print(f"\n{vang}--- Nhóm bắt đầu bằng chữ '{letter.upper()}' ---{reset_color}")
            for group in sorted(grouped[letter], key=lambda x: x['name']):
                print(f"{vang}{count}. {group['name']} (ID: {group['id']}){reset_color}")
                flat_list.append(group)
                count += 1
        return flat_list

    def select_group(self):
        groups = self.fetch_group_info()
        if not groups:
            return None
        flat_list = self.display_group_menu_grouped(groups)
        if not flat_list:
            return None
        while True:
            try:
                choice = int(input(f"{tim}Nhập số thứ tự của nhóm: {reset_color}").strip())
                if 1 <= choice <= len(flat_list):
                    self.group_name = flat_list[choice - 1]['name']
                    return flat_list[choice - 1]['id']
                print(f"{do}Số không hợp lệ.{reset_color}")
            except ValueError:
                print(f"{do}Vui lòng nhập số hợp lệ.{reset_color}")

    def send_full_content(self, thread_id, delay):
        try:
            if not self.file_content:
                print(f"{do}❌ File rỗng hoặc không có nội dung.{reset_color}")
                return
            self.running = True
            while self.running:
                self.setTyping(thread_id, ThreadType.GROUP)
                if self.use_mention:
                    mention = Mention("-1", offset=0, length=len(self.file_content))
                    self.send(Message(text=self.file_content, mention=mention), thread_id=thread_id, thread_type=ThreadType.GROUP)
                elif self.use_tagall_style:
                    mention = Mention("-1", offset=0, length=len(self.file_content))
                    styles = MultiMsgStyle([
                        MessageStyle(offset=0, length=len(self.file_content), style="color", color="#DB342E", auto_format=False),
                        MessageStyle(offset=0, length=len(self.file_content), style="bold", size="15", auto_format=False)
                    ])
                    self.send(Message(text=self.file_content, mention=mention, style=styles), thread_id=thread_id, thread_type=ThreadType.GROUP)
                else:
                    self.send(Message(text=self.file_content), thread_id=thread_id, thread_type=ThreadType.GROUP)
                time.sleep(delay)
        except Exception as e:
            print(f"{do}Lỗi khi gửi nội dung: {e}{reset_color}")

    def stop_sending(self):
        self.running = False
        print(f"{vang}⛔ Đã dừng gửi tin nhắn.{reset_color}")

active_accounts = []

def choose_txt_file():
    folder = "treo"
    files = [f for f in os.listdir(folder) if f.endswith('.txt')]
    if not files:
        print(f"{do}❌ Không có file .txt trong thư mục treo{reset_color}")
        return None
    print(vang + "\n📂 Danh sách file .txt:" + reset_color)
    for i, f in enumerate(files, 1):
        print(f"{i}. {f}")
    while True:
        try:
            idx = int(input(xanh_nhat + "\n💧 Chọn file: " + reset_color).strip())
            if 1 <= idx <= len(files):
                return os.path.join(folder, files[idx - 1])
            print(do + "❌ Số không hợp lệ" + reset_color)
        except ValueError:
            print(do + "❌ Nhập số nguyên" + reset_color)

def start_account_session():
    imei = input(f"{xanh_nhat}📱 Nhập IMEI: {reset_color}").strip()
    while True:
        cookie_str = input(f"{xanh_nhat}🍪 Nhập Cookie: {reset_color}").strip()
        cookie = validate_cookie(cookie_str)
        if cookie:
            break
    try:
        client = Bot(API_KEY, SECRET_KEY, imei=imei, session_cookies=cookie)
        print(f"{xanh_duong}Chọn chế độ treo:{reset_color}")
        print(f"{xanh_duong}[1] Gửi thường{reset_color}")
        print(f"{xanh_duong}[2] Gửi có mention (-1){reset_color}")
        print(f"{xanh_duong}[3] Gửi có mention (-1) + style đỏ đậm{reset_color}")
        while True:
            mode = input(f"{tim}Chọn chế độ (1-3): {reset_color}").strip()
            if mode in ['1', '2', '3']:
                break
            print(do + "❌ Chỉ được chọn 1, 2 hoặc 3" + reset_color)

        file_path = choose_txt_file()
        if not file_path:
            return

        with open(file_path, "r", encoding="utf-8") as f:
            client.file_content = f.read().strip()

        if mode == '2':
            client.use_mention = True
        elif mode == '3':
            client.use_tagall_style = True

        thread_id = client.select_group()
        if not thread_id:
            return

        try:
            delay = float(input(f"{xanh_nhat}⏱️ Nhập delay (giây): {reset_color}").strip())
        except ValueError:
            delay = 60

        t = threading.Thread(target=lambda: client.send_full_content(thread_id, delay), daemon=True)
        active_accounts.append({'thread': t, 'bot': client})
        t.start()

    except Exception as e:
        print(f"{do}❌ Cookie die hoặc lỗi đăng nhập: {e}{reset_color}")

def manage_accounts():
    while True:
        if not active_accounts:
            print(f"{do}❌ Không có acc nào đang chạy.{reset_color}")
            return
        print(f"\n{xanh_la}📋 Danh sách acc đang chạy:{reset_color}")
        for idx, acc in enumerate(active_accounts, start=1):
            print(f"{vang}{idx}. IMEI: {acc['bot'].imei} | Nhóm: {acc['bot'].group_name}{reset_color}")
        try:
            choice = int(input(f"\n{tim}Nhập số thứ tự acc muốn dừng (0 để quay lại): {reset_color}").strip())
            if choice == 0:
                return
            if 1 <= choice <= len(active_accounts):
                acc = active_accounts.pop(choice - 1)
                acc['bot'].stop_sending()
            else:
                print(f"{do}Số không hợp lệ.{reset_color}")
        except ValueError:
            print(f"{do}Vui lòng nhập số hợp lệ.{reset_color}")

def run_tool():
    os.system("clear")
    print(f"{xanh_duong}🔄 Tool treo đa tài khoản (Gõ 'addacc' để thêm acc){reset_color}")
    start_account_session()
    while True:
        user_input = input(f"{xanh_duong}➡️ Gõ 'addacc' để thêm acc, 'checkacc' để quản lý: {reset_color}").strip().lower()
        if user_input == 'addacc':
            start_account_session()
        elif user_input == 'checkacc':
            manage_accounts()

if __name__ == "__main__":
    run_tool()
