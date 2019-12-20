from app import create_app, db, dnsmasq_srv, accounting_srv
from app.models import RegistrationKey, Identity, Role, IpAddress, MacAddress, AddressPair, SupervisorAccount
from app.util import iptables_rules_manager, iptables_accounting_manager, shaping_manager, arp_manager
from datetime import datetime
import os
import atexit
import logging

def setup_logging():
    logging.basicConfig(format="[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S %z", level=logging.INFO)

def create_initital_db_entries():
    admin_role = Role.query.filter_by(role="Admin").first()
    if admin_role is None:
        db.session.add(Role(role="Admin"))
        
    helpdesk_role = Role.query.filter_by(role="Helpdesk").first()
    if helpdesk_role is None:
        db.session.add(Role(role="Helpdesk"))
        
    clerk_role = Role.query.filter_by(role="Clerk").first()
    if clerk_role is None:
        db.session.add(Role(role="Clerk"))

    admin_role = Role.query.filter_by(role="Admin").first()
    if SupervisorAccount.query.count() == 0:
        db.session.add(SupervisorAccount(username="admin",
                                         password="admin",
                                         first_name="Max",
                                         last_name="Mustermann",
                                         mail="admin.goerlitz@wh.studentenwerk-dresden.de",
                                         role=admin_role.id,
                                         notify_shaping=True,
                                         notify_login_attempts=True,
                                         notify_critical_events=True))

    db.session.commit()

def firewall_unlock_registered_devices():
    with app.app_context():
        address_column = IpAddress.query.with_entities(IpAddress.address_v4).all()
        for row in address_column:
            ip_address = row[0]
            ip_address_query = IpAddress.query.filter_by(address_v4=ip_address).first()
            address_pair_query = AddressPair.query.filter_by(ip_address=ip_address_query.id).first()
            reg_key_query = RegistrationKey.query.filter_by(id=address_pair_query.reg_key).first()
            if reg_key_query.active is True:
                iptables_rules_manager.unlock_registered_device(ip_address)

def firewall_relock_unregistered_devices():
    with app.app_context():
        address_column = IpAddress.query.with_entities(IpAddress.address_v4).all()
        for row in address_column:
            ip_address = row[0]
            ip_address_query = IpAddress.query.filter_by(address_v4=ip_address).first()
            address_pair_query = AddressPair.query.filter_by(ip_address=ip_address_query.id).first()
            reg_key_query = RegistrationKey.query.filter_by(id=address_pair_query.reg_key).first()
            if reg_key_query.active is True:
                iptables_rules_manager.relock_registered_device(ip_address)

def setup_accounting_chains():
    with app.app_context():
        address_pair_query = db.session.query(AddressPair.reg_key).filter(AddressPair.reg_key).distinct()
        for reg_key_fk in address_pair_query:
            if reg_key_fk is None:
                continue

            reg_key_query = RegistrationKey.query.filter_by(id=reg_key_fk.reg_key).first()
            if reg_key_query is None:
                continue

            iptables_accounting_manager.add_accounter_chain(reg_key_query.id)

        address_pair_query = db.session.query(AddressPair.ip_address).filter(AddressPair.ip_address).distinct()
        for ip_address_fk in address_pair_query:
            if ip_address_fk is None:
                continue

            ip_address_query = IpAddress.query.filter_by(id=ip_address_fk.ip_address).first()
            if ip_address_query is None:
                continue

            address_pair_query = AddressPair.query.filter_by(ip_address=ip_address_fk.ip_address).first()
            reg_key_query = RegistrationKey.query.filter_by(id=address_pair_query.reg_key).first()
            ip_address_query = IpAddress.query.filter_by(id=address_pair_query.ip_address).first()
            iptables_accounting_manager.add_ip_to_box(reg_key_query.id, ip_address_query.address_v4)
            # Spoofing Protection
            mac_address_query = MacAddress.query.filter_by(id=address_pair_query.mac_address).first()
            arp_manager.add_static_arp_entry(ip_address_query.address_v4, mac_address_query.address)

def remove_accounting_chains():
    with app.app_context():
        address_pair_query = db.session.query(AddressPair.ip_address).filter(AddressPair.ip_address).distinct()
        for ip_address_fk in address_pair_query:
            if ip_address_fk is None:
                continue

            ip_address_query = IpAddress.query.filter_by(id=ip_address_fk.ip_address).first()
            if ip_address_query is None:
                continue

            address_pair_query = AddressPair.query.filter_by(ip_address=ip_address_fk.ip_address).first()
            reg_key_query = RegistrationKey.query.filter_by(id=address_pair_query.reg_key).first()
            ip_address_query = IpAddress.query.filter_by(id=address_pair_query.ip_address).first()
            iptables_accounting_manager.remove_ip_from_box(reg_key_query.id, ip_address_query.address_v4)
            # Spoofing Protection
            arp_manager.remove_static_arp_entry(ip_address_query.address_v4)

        address_pair_query = db.session.query(AddressPair.reg_key).filter(AddressPair.reg_key).distinct()
        for reg_key_fk in address_pair_query:
            if reg_key_fk is None:
                continue

            reg_key_query = RegistrationKey.query.filter_by(id=reg_key_fk.reg_key).first()
            if reg_key_query is None:
                continue

            iptables_accounting_manager.remove_accounter_chain(reg_key_query.id)

def shutdown():
    # Stop dnsmasq
    dnsmasq_srv.stop()

    # Clear Firewall Rules
    iptables_rules_manager.apply_block_rule(delete=True)
    iptables_rules_manager.apply_redirect_rule(delete=True)
    iptables_rules_manager.apply_dns_rule(delete=True)
    firewall_relock_unregistered_devices()

    # Stop Accounting
    accounting_srv.stop()
    remove_accounting_chains()

    # Shutdown Shaping
    shaping_manager.shutdown_shaping()

    logging.info("Network not managed anymore")

def startup():
    with app.app_context():
        db.create_all()
        create_initital_db_entries()

    # Start dnsmasq
    dnsmasq_srv.start()

    # Setup Shaping
    shaping_manager.setup_shaping()

    # Start Accounting
    setup_accounting_chains()
    accounting_srv.app = app
    accounting_srv.start(10)

    # Apply Firewall Rules
    iptables_rules_manager.apply_block_rule(delete=False)
    iptables_rules_manager.apply_redirect_rule(delete=False)
    iptables_rules_manager.apply_dns_rule(delete=False)
    firewall_unlock_registered_devices()

    atexit.register(shutdown)

    logging.info("Network now fully managed")
    logging.info("Startup completed in " + str((datetime.now() - before_startup).total_seconds()) + "s")

before_startup = datetime.now()
setup_logging()
app = create_app("production")
startup()
