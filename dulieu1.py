import threading
import time
import os
import json
import random
from collections import defaultdict
from zlapi import ZaloAPI, ThreadType, Message
from zlapi.models import Mention, MessageStyle, MultiMsgStyle
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
        self.is_spamstk_running = False
        self.file_content = ""
        self.use_mention = False
        self.use_tagall_style = False
        self.mode = "1"

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
        flat_list = []
        count = 1
        for group in groups:
            first_letter = group['name'][0].lower()
            grouped[first_letter].append(group)
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

    def choose_txt_file_treo(self):
        folder = "treo"
        files = [f for f in os.listdir(folder) if f.endswith('.txt')]
        if not files:
            print(f"{do}❌ Không có file .txt trong thư mục treo{reset_color}")
            return None
        print(vang + "\n📂 Danh sách file .txt trong treo:" + reset_color)
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

    def send_full_content(self, thread_id, delay):
        try:
            if not self.file_content:
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
        except:
            pass

    def list_group_members(self, thread_id):
        try:
            group = super().fetchGroupInfo(thread_id)["gridInfoMap"][thread_id]
            members = group["memVerList"]
            members_list = []
            for index, member in enumerate(members, start=1):
                uid = member.split('_')[0]
                user_info = super().fetchUserInfo(uid)
                author_info = user_info.get("changed_profiles", {}).get(uid, {})
                name = author_info.get('zaloName', 'Không xác định')
                members_list.append({"uid": uid, "name": name})
                print(f"{index}. {name} (UID: {uid})")
            choice = int(input("Nhập số để chọn thành viên: ")) - 1
            return members_list[choice] if 0 <= choice < len(members_list) else None
        except:
            return None

    def send_reo_file(self, thread_id, mentioned_user_id, mentioned_name, filename, delay, enable_sticker, stk_delay):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                base_lines = [line.strip() for line in f if line.strip()]
                if not base_lines:
                    return
                remaining_lines = []
                self.running = True
                self.is_spamstk_running = enable_sticker

                def spam_loop():
                    nonlocal remaining_lines
                    while self.running:
                        if not remaining_lines:
                            remaining_lines = base_lines.copy()
                            random.shuffle(remaining_lines)
                        phrase = remaining_lines.pop()
                        mention_text = "@1"
                        message_text = f"{phrase} =))=))=))=)) {mention_text}"
                        offset = message_text.index(mention_text)
                        mention = Mention(uid=mentioned_user_id, offset=offset, length=len(mention_text))
                        full_message = Message(text=message_text, mention=mention)
                        self.setTyping(thread_id, ThreadType.GROUP)
                        time.sleep(1.5)
                        self.send(full_message, thread_id=thread_id, thread_type=ThreadType.GROUP)
                        time.sleep(delay)

                def spamstk_loop():
                    while self.is_spamstk_running:
                        try:
                            self.sendSticker(
                                stickerType=3,
                                stickerId=21979,
                                cateId=10136,
                                thread_id=thread_id,
                                thread_type=ThreadType.GROUP
                            )
                        except:
                            pass
                        time.sleep(stk_delay)

                t1 = threading.Thread(target=spam_loop)
                t1.daemon = True
                t1.start()

                if enable_sticker:
                    t2 = threading.Thread(target=spamstk_loop)
                    t2.daemon = True
                    t2.start()

                while self.running:
                    time.sleep(1)
        except:
            pass

    def stop_sending(self):
        self.running = False
        self.is_spamstk_running = False

active_accounts = []

def start_account_session():
    imei = input(f"{xanh_nhat}📱 Nhập IMEI: {reset_color}").strip()
    while True:
        cookie_str = input(f"{xanh_nhat}🍪 Nhập Cookie: {reset_color}").strip()
        cookie = validate_cookie(cookie_str)
        if cookie:
            break
    try:
        client = Bot(API_KEY, SECRET_KEY, imei=imei, session_cookies=cookie)
        print(f"{xanh_duong}Chọn chế độ:{reset_color}")
        print(f"[1] Gửi thường")
        print(f"[2] Gửi có mention (-1)")
        print(f"[3] Gửi có mention + style")
        print(f"[4] Nhây réo tag")
        while True:
            mode = input(f"{tim}Chọn chế độ (1-4): {reset_color}").strip()
            if mode in ['1','2','3','4']:
                client.mode = mode
                break

        thread_id = client.select_group()
        if not thread_id:
            return

        if mode in ['1','2','3']:
            file_path = client.choose_txt_file_treo()
            if not file_path:
                return
            with open(file_path, "r", encoding="utf-8") as f:
                client.file_content = f.read().strip()
            if mode == '2':
                client.use_mention = True
            elif mode == '3':
                client.use_tagall_style = True
            try:
                delay = float(input(f"{xanh_nhat}⏱️ Nhập delay (giây): {reset_color}").strip())
            except:
                delay = 60
            t = threading.Thread(target=lambda: client.send_full_content(thread_id, delay), daemon=True)
            active_accounts.append({'thread': t, 'bot': client})
            t.start()

        elif mode == '4':
            try:
                delay = float(input(f"{xanh_nhat}⏱️ Nhập delay gửi tin (giây): {reset_color}").strip())
            except:
                delay = 60
            filename = input(f"{xanh_nhat}Nhập file txt để gửi: {reset_color}").strip()
            enable_sticker = input(f"{xanh_nhat}Bật sticker không? (y/n): {reset_color}").lower() == 'y'
            stk_delay = 5
            if enable_sticker:
                try:
                    stk_delay = float(input(f"{xanh_nhat}Nhập delay sticker (giây): {reset_color}").strip())
                except:
                    stk_delay = 5
            selected_member = client.list_group_members(thread_id)
            if not selected_member:
                return
            t = threading.Thread(target=lambda: client.send_reo_file(thread_id, selected_member['uid'], selected_member['name'], filename, delay, enable_sticker, stk_delay), daemon=True)
            active_accounts.append({'thread': t, 'bot': client})
            t.start()

    except:
        pass

def manage_accounts():
    while True:
        if not active_accounts:
            return
        for idx, acc in enumerate(active_accounts, start=1):
            group_display_name = acc['bot'].group_name
            if acc['bot'].mode == '4':
                group_display_name += " (nhây)"
            print(f"{idx}. Nhóm: {group_display_name} | IMEI: {acc['bot'].imei}")
        try:
            choice = int(input("Nhập số thứ tự acc muốn dừng (0 để quay lại): ").strip())
            if choice == 0:
                return
            if 1 <= choice <= len(active_accounts):
                acc = active_accounts.pop(choice - 1)
                acc['bot'].stop_sending()
        except:
            pass

def run_tool():
    os.system("clear")
    start_account_session()
    while True:
        user_input = input(f"{xanh_duong}➡️ Gõ 'addacc' để thêm acc, 'checkacc' để quản lý: {reset_color}").strip().lower()
        if user_input == 'addacc':
            start_account_session()
        elif user_input == 'checkacc':
            manage_accounts()

if __name__ == "__main__":
    run_tool()
