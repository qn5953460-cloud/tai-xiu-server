import asyncio
import random
import socketio
from aiohttp import web

# Khởi tạo Socket.IO Server
sio = socketio.AsyncServer(cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

# Trạng thái toàn cục
online_count = 0
time_left = 15
dice_results = [1, 1, 1]
game_state = "BETTING"  # "BETTING" hoặc "RESULT"

async def game_loop():
    global time_left, dice_results, game_state
    while True:
        await asyncio.sleep(1)
        
        if game_state == "BETTING":
            time_left -= 1
            # Đồng bộ trạng thái thời gian và số online cho client
            await sio.emit('sync_game_state', {
                'time_left': time_left,
                'waiting_for_open': False,
                'online_count': online_count
            })
            
            if time_left <= 0:
                game_state = "RESULT"
                dice_results = [random.randint(1, 6) for _ in range(3)]
                total_score = sum(dice_results)
                
                # Phân định TÀI hay XỈU
                result_side = "TAI" if total_score >= 11 else "XIU"
                hist_char = "T" if result_side == "TAI" else "X"
                
                # Gửi kết quả chính xác cho client
                await sio.emit('game_result', {
                    'dice': dice_results,
                    'total': total_score,
                    'result_side': result_side,
                    'hist_char': hist_char
                })
                
                # Chờ 5 giây xem kết quả
                await asyncio.sleep(5)
                
                # Reset ván mới
                game_state = "BETTING"
                time_left = 15

@sio.event
async def connect(sid, environ):
    global online_count
    online_count += 1
    print(f"[+] Người chơi kết nối: {sid} | Tổng online: {online_count}")
    await sio.emit('sync_game_state', {
        'time_left': time_left,
        'waiting_for_open': (game_state == "RESULT"),
        'online_count': online_count,
        'dice': dice_results
    })

@sio.event
async def disconnect(sid):
    global online_count
    online_count -= 1
    print(f"[-] Người chơi ngắt kết nối: {sid} | Tổng online: {online_count}")
    await sio.emit('sync_game_state', {
        'time_left': time_left,
        'waiting_for_open': (game_state == "RESULT"),
        'online_count': online_count,
        'dice': dice_results
    })

@sio.event
async def place_bet(sid, data):
    side = data.get('side')
    amount = data.get('amount')
    print(f"Người chơi {sid[:4]} vừa đặt {amount:,}d vào {side}")
    
    # Gửi thông báo chat về số tiền cược đúng key 'message' mà client yêu cầu
    await sio.emit('new_chat', {
        'sender': f"VIP_{sid[:3]}", 
        'message': f"Đã cược {amount:,}d vào {side}",
        'color': [200, 220, 255]
    })

@sio.event
async def send_chat(sid, data):
    message = data.get('message', '')
    if message:
        await sio.emit('new_chat', {
            'sender': f"VIP_{sid[:3]}",
            'message': message,
            'color': [220, 220, 220]
        })

async def init_app():
    asyncio.create_task(game_loop())
    return app

if __name__ == '__main__':
    print("🚀 Đang khởi động Server Tài Xỉu tại cổng 8080...")
    web.run_app(init_app(), port=8080)