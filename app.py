from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS # Bu satırı ekleyin!
from datetime import datetime
import os

app = Flask(__name__)
CORS(app) # BURADA OLMALI!

# --- Veritabanı Ayarları ---
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://galataport_user:GUiENjNBJyCiVKeYUpbaK6tgvs71Dy5n@dpg-d1r41bbipnbc73f14u70-a/galataport')
# KENDİ RENDER URL'NİZİ BURAYA YAPIŞTIRDIĞINIZDAN EMİN OLUN!

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Veritabanı Modelleri ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'manager', 'technician'
    device_id = db.Column(db.String(255), unique=True, nullable=True) # Android ID için
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "device_id": self.device_id
        }

class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    bluetooth_mac = db.Column(db.String(17), unique=True, nullable=False)
    friendly_name = db.Column(db.String(100), unique=True, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "bluetooth_mac": self.bluetooth_mac,
            "friendly_name": self.friendly_name,
            "is_active": self.is_active
        }

class MachineAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship('User', backref=db.backref('assignments', lazy=True))
    machine = db.relationship('Machine', backref=db.backref('assignments', lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "machine_id": self.machine_id,
            "username": self.user.username,
            "machine_name": self.machine.name,
            "friendly_machine_name": self.machine.friendly_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None
        }

class UsageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)

    user = db.relationship('User', backref=db.backref('usage_logs', lazy=True))
    machine = db.relationship('Machine', backref=db.backref('usage_logs', lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "machine_id": self.machine_id,
            "username": self.user.username,
            "machine_name": self.machine.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes
        }

# --- API Endpoint'leri ---

@app.cli.command("initdb")
def initdb_command():
    """Veritabanı tablolarını oluşturur ve örnek veriler ekler."""
    db.drop_all() # Mevcut tabloları temizle (Geliştirme için)
    db.create_all()
    
    # Örnek Kullanıcılar
    admin_user = User(username='admin', password='adminpass', role='admin', device_id='admin_device_id_example')
    manager_user = User(username='yonetici', password='managerpass', role='manager', device_id='manager_device_id_example')
    tech1 = User(username='makineci1', password='pass123', role='technician', device_id='tech1_device_id_example')
    tech2 = User(username='makineci2', password='pass123', role='technician', device_id='tech2_device_id_example')
    
    db.session.add_all([admin_user, manager_user, tech1, tech2])
    db.session.commit()

    # Örnek Makineler
    machine1 = Machine(name='Zemin Temizleyici 1', bluetooth_mac='08:D1:F9:E9:C2:CE', friendly_name='Makine 855-4')
    machine2 = Machine(name='Cila Makinesi 2', bluetooth_mac='F4:CF:A2:XX:XX:YY', friendly_name='Makine ABC') # Kendi MAC'lerinizi yazın
    machine3 = Machine(name='Vakumlu Süpürge 3', bluetooth_mac='AC:D1:F9:YY:YY:ZZ', friendly_name='Makine DEF') # Kendi MAC'lerinizi yazın

    db.session.add_all([machine1, machine2, machine3])
    db.session.commit()

    # Örnek Atamalar (makineci1 Makine 855-4 ve Makine ABC'yi kullanabilir)
    assign1 = MachineAssignment(user_id=tech1.id, machine_id=machine1.id)
    assign2 = MachineAssignment(user_id=tech1.id, machine_id=machine2.id)
    
    db.session.add_all([assign1, assign2])
    db.session.commit()

    print("Veritabanı tabloları oluşturuldu ve örnek veriler eklendi.")

@app.route('/')
def home():
    return "Merhaba Galataport Backend API! Veritabanı entegrasyonu tamamlandı."

# Kullanıcı kimlik doğrulama endpoint'i
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    device_id = data.get('device_id')

    user = None
    if username and password:
        user = User.query.filter_by(username=username, password=password).first()
    elif device_id:
        user = User.query.filter_by(device_id=device_id).first()

    if user:
        return jsonify({
            "message": "Giriş başarılı",
            "user": user.to_dict(),
            "role": user.role
        }), 200
    else:
        return jsonify({"message": "Geçersiz kimlik bilgileri veya yetkisiz cihaz"}), 401

# --- Admin Panel API Endpoint'leri ---

# Tüm kullanıcıları listeleme
@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

# Yeni kullanıcı ekleme
@app.route('/users', methods=['POST'])
def add_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    device_id = data.get('device_id') # None olabilir

    if not username or not password or not role:
        return jsonify({"message": "Kullanıcı adı, şifre ve rol zorunludur"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Kullanıcı adı zaten mevcut"}), 409
    if device_id and User.query.filter_by(device_id=device_id).first():
        return jsonify({"message": "Cihaz ID'si zaten başka bir kullanıcıya atanmış"}), 409

    new_user = User(username=username, password=password, role=role, device_id=device_id)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Kullanıcı başarıyla eklendi", "user": new_user.to_dict()}), 201

# Kullanıcı silme
@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "Kullanıcı bulunamadı"}), 404
    
    # Kullanıcıya ait atamaları ve logları da sil (önemli!)
    MachineAssignment.query.filter_by(user_id=user_id).delete()
    UsageLog.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Kullanıcı başarıyla silindi"}), 200

# Tüm makineleri listeleme
@app.route('/machines', methods=['GET'])
def get_machines():
    machines_data = [machine.to_dict() for machine in Machine.query.all()]
    return jsonify(machines_data), 200

# Yeni makine ekleme
@app.route('/machines', methods=['POST'])
def add_machine():
    data = request.get_json()
    name = data.get('name')
    friendly_name = data.get('friendly_name')
    bluetooth_mac = data.get('bluetooth_mac')

    if not name or not bluetooth_mac:
        return jsonify({"message": "Makine adı ve Bluetooth MAC adresi zorunludur"}), 400
    
    # MAC adresi format kontrolü eklenebilir

    if Machine.query.filter_by(bluetooth_mac=bluetooth_mac).first():
        return jsonify({"message": "Bu MAC adresine sahip makine zaten mevcut"}), 409

    new_machine = Machine(name=name, friendly_name=friendly_name, bluetooth_mac=bluetooth_mac)
    db.session.add(new_machine)
    db.session.commit()
    return jsonify({"message": "Makine başarıyla eklendi", "machine": new_machine.to_dict()}), 201

# Makine silme
@app.route('/machines/<int:machine_id>', methods=['DELETE'])
def delete_machine(machine_id):
    machine = Machine.query.get(machine_id)
    if not machine:
        return jsonify({"message": "Makine bulunamadı"}), 404
    
    # Makineye ait atamaları ve logları da sil (önemli!)
    MachineAssignment.query.filter_by(machine_id=machine_id).delete()
    UsageLog.query.filter_by(machine_id=machine_id).delete()
    db.session.delete(machine)
    db.session.commit()
    return jsonify({"message": "Makine başarıyla silindi"}), 200

# Kullanıcıya atanmış makineleri listeleme (mobil uygulama için)
@app.route('/my_machines/<int:user_id>', methods=['GET'])
def get_my_machines(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "Kullanıcı bulunamadı"}), 404

    assigned_machines = []
    if user.role == 'admin' or user.role == 'manager':
        assigned_machines = [m.to_dict() for m in Machine.query.filter_by(is_active=True).all()]
    elif user.role == 'technician':
        assignments = MachineAssignment.query.filter_by(user_id=user.id).all()
        for assignment in assignments:
            if assignment.machine.is_active:
                assigned_machines.append(assignment.machine.to_dict())
    
    return jsonify(assigned_machines), 200

# Makine kullanımı başlatma endpoint'i
@app.route('/usage/start', methods=['POST'])
def start_usage():
    data = request.get_json()
    user_id = data.get('user_id')
    machine_mac = data.get('machine_mac')

    user = User.query.get(user_id)
    machine = Machine.query.filter_by(bluetooth_mac=machine_mac).first()

    if not user or not machine:
        return jsonify({"message": "Kullanıcı veya makine bulunamadı"}), 404
    
    if user.role == 'technician':
        assignment = MachineAssignment.query.filter_by(user_id=user.id, machine_id=machine.id).first()
        if not assignment:
            return jsonify({"message": "Bu makineyi kullanmaya yetkiniz yok"}), 403

    # Eğer makine şu an kullanımda ise (devam eden bir log varsa), eskiyi bitirip yeni başlatma mantığı eklenebilir.
    # Şimdilik basitçe yeni bir log başlatıyoruz.
    new_log = UsageLog(user_id=user.id, machine_id=machine.id, start_time=datetime.utcnow())
    db.session.add(new_log)
    db.session.commit()
    return jsonify({"message": "Kullanım başlatıldı", "log_id": new_log.id}), 200

# Makine kullanımı sonlandırma endpoint'i
@app.route('/usage/end', methods=['POST'])
def end_usage():
    data = request.get_json()
    log_id = data.get('log_id')
    end_time = datetime.utcnow()

    log = UsageLog.query.get(log_id)
    if not log:
        return jsonify({"message": "Kullanım kaydı bulunamadı"}), 404
    
    log.end_time = end_time
    duration_seconds = (end_time - log.start_time).total_seconds()
    log.duration_minutes = int(duration_seconds / 60)
    
    db.session.commit()
    return jsonify({"message": "Kullanım sonlandırıldı", "log": log.to_dict()}), 200

# Tüm kullanım loglarını listeleme (Admin/Yönetici için)
@app.route('/usage_logs', methods=['GET'])
def get_usage_logs():
    logs_data = []
    logs = UsageLog.query.order_by(UsageLog.start_time.desc()).all()
    for log in logs:
        log_dict = log.to_dict()
        # LogDict'e kullanıcı adı ve makine adını da ekleyelim kolaylık için
        log_dict['username'] = log.user.username if log.user else 'Bilinmiyor'
        log_dict['machine_name'] = log.machine.name if log.machine else 'Bilinmiyor'
        logs_data.append(log_dict)
    return jsonify(logs_data), 200
    
@app.route('/register_device', methods=['POST'])
def register_device():
    data = request.get_json()
    name = data.get('name')
    surname = data.get('surname')
    device_id = data.get('device_id')

    if not name or not surname or not device_id:
        return jsonify({"message": "Ad, Soyad ve Cihaz ID zorunludur"}), 400

    # device_id zaten kayıtlı mı kontrol et
    existing_user_with_device = User.query.filter_by(device_id=device_id).first()
    if existing_user_with_device:
        return jsonify({"message": "Bu cihaz ID'si zaten kayıtlı"}), 409 # Conflict

    # Kullanıcı adı olarak ad ve soyadı birleştir
    username = f"{name.lower().replace(' ', '')}.{surname.lower().replace(' ', '')}"
    # Basit bir şifre (admin tarafından atanacak veya varsayılan)
    # Şimdilik varsayılan bir şifre koyalım, admin panelinden değiştirilebilir
    password = "default_password" # Buraya güvenli bir varsayılan şifre belirleyin

    # Yeni kullanıcı oluştur, rolü 'pending' veya 'unassigned' olarak belirleyelim
    # Admin tarafından atanana kadar yetkisiz kalacak
    new_user = User(username=username, password=password, role='pending', device_id=device_id)

    # Eğer aynı kullanıcı adı zaten varsa (çakışma olabilir)
    # user_count = User.query.filter_by(username=username).count()
    # if user_count > 0:
    #     username = f"{username}{user_count + 1}" # Kullanıcı adını benzersiz yap

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Cihaz başarıyla kaydedildi, yönetici onayı bekleniyor", "user_id": new_user.id}), 201
    
    @app.route('/users/<int:user_id>', methods=['PUT']) # veya PATCH
    def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "Kullanıcı bulunamadı"}), 404

    data = request.get_json()
    new_role = data.get('role')
    new_device_id = data.get('device_id') # None olabilir

    if new_role:
        user.role = new_role

    # Eğer yeni device_id varsa ve başka bir kullanıcıya atanmamışsa güncelle
    if new_device_id:
        existing_user_with_new_device = User.query.filter(User.device_id == new_device_id, User.id != user_id).first()
        if existing_user_with_new_device:
            return jsonify({"message": "Bu cihaz ID'si zaten başka bir kullanıcıya atanmış"}), 409
        user.device_id = new_device_id
    else: # Eğer device_id boş gönderilmişse (yani temizlemek isteniyorsa)
        user.device_id = None # Veya boş string ''

    db.session.commit()
    return jsonify({"message": "Kullanıcı başarıyla güncellendi", "user": user.to_dict()}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)