class Config:
    SECRET_KEY = "BnUlPYIj2ZzeTL1wv4IxzCsRtqcPJLpxvOv"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def init_app(app):
        pass


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = "mysql://traffy_user:traffy_user@192.168.100.150/traffy"

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)


config = {
    'production': ProductionConfig,
    'default': ProductionConfig
}

LANGUAGES = ["en", "de"]
DNSMASQ_CONFIG_FILE = "/home/traffy/dnsmasq/dnsmasq.conf"
DNSMASQ_HOSTS_FILE = "/home/traffy/dnsmasq/dnsmasq-hosts.conf"
DNSMASQ_LEASE_FILE = "/home/traffy/dnsmasq/dnsmasq.leases"
DNSMASQ_LISTEN_INTERFACE = "enp7s0"
DNS_SERVER = "141.46.140.31"
DAILY_TOPUP_VOLUME = 5368709120 # 5 GiB / in bytes
MAX_SAVED_VOLUME = 37580963840 # 35 GiB / in bytes
SHAPING_SPEED = "64kbit"
SHAPING_EXCEPTIONS = ["192.168.100.150", "192.168.100.201", "88.198.248.254"]
MAX_MAC_ADDRESSES_PER_REG_KEY = 3
IP_RANGE_START = "10.90.0.2"
IP_RANGE_END = "10.90.0.254"
THIS_SERVER_IP = "10.90.0.1"

ADMIN_NAME = "Falk Seidl"
ADMIN_MAIL = "admin.goerlitz@wh.studentenwerk-dresden.de"
ADMIN_ROOM = "2521"

COMMUNITY = "Görlitz"
SMTP_SERVER = "smtp.hszg.de"
SMTP_PORT = "25"