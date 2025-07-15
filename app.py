from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# --- Veritabanı Ayarları ---
# Render'dan aldığınız External Database URL'sini buraya yapıştırın.
# Güvenlik için, bu URL'yi doğrudan koda yazmak yerine çevre değişkeni (environment variable) olarak kullanmak daha iyidir.
# Şimdilik direkt yazalım, Render'a dağıtırken çevre değişkenine çeviririz.
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://galataport_user:GUiENjNBJyCiVKeYUpbaK6tgvs71Dy5n@dpg-d1r41bbipnbc73f14u70-a.oregon-postgres.render.com/galataport')
# YUKARIDAKİ 'postgresql://your_user:your_password@your_host:your_port/your_database' KISMINI KENDİ RENDER URL'NİZLE DEĞİŞTİRİN!

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Bellek tüketimini azaltmak için False yapın
db = SQLAlchemy(app)

# --- Veritabanı Modelleri ---
# Kullanıcılar tablosu (Admin, Yönetici, Makineci)
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

# Makineler tablosu
class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # "Zemin Temizleyici 1"
    bluetooth_mac = db.Column(db.String(17), unique=True, nullable=False) # "08:D1:F9:E9:C2:CE"
    friendly_name = db.Column(db.String(100), unique=True, nullable=True) # "Makine 855-4"
    is_active = db.Column(db.Boolean, default=True) # Makine aktif mi, pasif mi?

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "bluetooth_mac": self.bluetooth_mac,
            "friendly_name": self.friendly_name,
            "is_active": self.is_active
        }

# Kullanıcı-Makine Atamaları (Kim hangi makineyi kullanabilir)
class MachineAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow) # Atamanın başladığı zaman
    end_date = db.Column(db.DateTime, nullable=True) # Atamanın bittiği zaman (istenirse)

    # Bu atamanın hangi vardiyalarda geçerli olduğunu da buraya ekleyebiliriz (şimdilik basit tutalım)

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

# Kullanım Logları (Kim, hangi makineyi, ne zaman kullandı)
class UsageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True) # Dakika cinsinden kullanım süresi

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

# İlk çalıştırmada veritabanı tablolarını oluşturmak ve örnek veri eklemek için.
# Sadece geliştirme ortamında çalıştırılmalı!
@app.cli.command("initdb")
def initdb_command():
    """Veritabanı tablolarını oluşturur ve örnek veriler ekler."""
    db.create_all()

    # Örnek Kullanıcılar
    admin_user = User(username='admin', password='adminpass', role='admin', device_id='admin_device_id_example')
    manager_user = User(username='yonetici', password='managerpass', role='manager', device_id='manager_device_id_example')
    tech1 = User(username='makineci1', password='pass123', role='technician', device_id='tech1_device_id_example')
    tech2 = User(username='makineci2', password='pass123', role='technician', device_id='tech2_device_id_example')

    db.session.add_all([admin_user, manager_user, tech1, tech2])
    db.session.commit() # Kullanıcıları kaydet ki ID'leri oluşsun

    # Örnek Makineler
    machine1 = Machine(name='Zemin Temizleyici 1', bluetooth_mac='08:D1:F9:E9:C2:CE', friendly_name='Makine 855-4')
    machine2 = Machine(name='Cila Makinesi 2', bluetooth_mac='F4:CF:A2:XX:XX:YY', friendly_name='Makine ABC') # Kendi MAC'lerinizi yazın
    machine3 = Machine(name='Vakumlu Süpürge 3', bluetooth_mac='AC:D1:F9:YY:YY:ZZ', friendly_name='Makine DEF') # Kendi MAC'lerinizi yazın

    db.session.add_all([machine1, machine2, machine3])
    db.session.commit() # Makineleri kaydet ki ID'leri oluşsun

    # Örnek Atamalar (makineci1 Makine 855-4 ve Makine ABC'yi kullanabilir)
    assign1 = MachineAssignment(user_id=tech1.id, machine_id=machine1.id)
    assign2 = MachineAssignment(user_id=tech1.id, machine_id=machine2.id)

    db.session.add_all([assign1, assign2])
    db.session.commit()

    print("Veritabanı tabloları oluşturuldu ve örnek veriler eklendi.")

@app.route('/')
def home():
    return "Merhaba Galataport Backend API! Veritabanı entegrasyonu tamamlandı."

# Kullanıcı kimlik doğrulama endpoint'i (username/password veya device_id ile)
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    device_id = data.get('device_id') # Android ID'sini almak için

    user = None
    if username and password: # Kullanıcı adı ve şifre ile giriş
        user = User.query.filter_by(username=username, password=password).first()
    elif device_id: # Sadece device_id ile giriş (Admin'in atadığı telefonlar için)
        user = User.query.filter_by(device_id=device_id).first()
        if not user: # Eğer device_id ile bulunamazsa, kullanıcı adı şifre de deneyebiliriz
             if username and password:
                 user = User.query.filter_by(username=username, password=password).first()


    if user:
        return jsonify({
            "message": "Giriş başarılı",
            "user": user.to_dict(), # Kullanıcı bilgilerini döndür
            "role": user.role
        }), 200
    else:
        return jsonify({"message": "Geçersiz kimlik bilgileri veya yetkisiz cihaz"}), 401

# Tüm makineleri listeleme endpoint'i (yetkilendirmeye sonra bakarız)
@app.route('/machines', methods=['GET'])
def get_machines():
    machines_data = [machine.to_dict() for machine in Machine.query.all()]
    return jsonify(machines_data), 200

# Kullanıcıya atanmış makineleri listeleme endpoint'i (role göre filtreleme)
@app.route('/my_machines/<int:user_id>', methods=['GET'])
def get_my_machines(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "Kullanıcı bulunamadı"}), 404

    assigned_machines = []
    if user.role == 'admin' or user.role == 'manager':
        # Admin veya yönetici tüm aktif makineleri görebilir (şimdilik)
        assigned_machines = [m.to_dict() for m in Machine.query.filter_by(is_active=True).all()]
    elif user.role == 'technician':
        # Makineci sadece kendisine atanmış makineleri görebilir
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

    # Yetki kontrolü (şimdilik basit: atanmışsa veya admin/manager ise)
    if user.role == 'technician':
        assignment = MachineAssignment.query.filter_by(user_id=user.id, machine_id=machine.id).first()
        if not assignment:
            return jsonify({"message": "Bu makineyi kullanmaya yetkiniz yok"}), 403

    # Eğer makine zaten kullanılıyorsa, mevcut log'u sonlandırabiliriz veya hata verebiliriz
    # Şimdilik basitçe yeni bir log başlatıyoruz.
    new_log = UsageLog(user_id=user.id, machine_id=machine.id, start_time=datetime.utcnow())
    db.session.add(new_log)
    db.session.commit()
    return jsonify({"message": "Kullanım başlatıldı", "log_id": new_log.id}), 200

# Makine kullanımı sonlandırma endpoint'i
@app.route('/usage/end', methods=['POST'])
def end_usage():
    data = request.get_json()
    log_id = data.get('log_id') # Başlatma sırasında dönen log_id
    end_time = datetime.utcnow()

    log = UsageLog.query.get(log_id)
    if not log:
        return jsonify({"message": "Kullanım kaydı bulunamadı"}), 404

    log.end_time = end_time
    # Süre hesaplama (dakika cinsinden)
    duration_seconds = (end_time - log.start_time).total_seconds()
    log.duration_minutes = int(duration_seconds / 60)

    db.session.commit()
    return jsonify({"message": "Kullanım sonlandırıldı", "log": log.to_dict()}), 200

# Tüm kullanım loglarını listeleme (Admin/Yönetici için)
@app.route('/usage_logs', methods=['GET'])
def get_usage_logs():
    logs_data = [log.to_dict() for log in UsageLog.query.order_by(UsageLog.start_time.desc()).all()]
    return jsonify(logs_data), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)