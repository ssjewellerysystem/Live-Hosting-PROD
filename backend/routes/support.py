from flask import Blueprint, request, jsonify
from backend.models.support import SupportModel, FAQModel, SupportLinkModel
from backend.middleware.auth import admin_required, token_required

support_bp = Blueprint('support', __name__)

ALLOWED_SUPPORT_URL_PREFIXES = ("https://", "http://", "mailto:", "tel:", "/")


def _is_valid_support_url(url):
    normalized = str(url or "").strip().lower()
    return normalized.startswith(ALLOWED_SUPPORT_URL_PREFIXES) and not normalized.startswith("//")

# List of beginner-friendly FAQs for initial seeding
DEFAULT_FAQS = [
    {
        "question": "What is SSJewellery?",
        "answer": "SSJewellery is a premier luxury jewelry store offering masterfully crafted diamond solitaire rings, emerald necklaces, and designer bridal collections."
    },
    {
        "question": "What certifications do you provide?",
        "answer": "All our diamonds are certified by international grading laboratories (such as GIA or IGI), and all gold jewelry carries the official BIS Hallmark certification."
    },
    {
        "question": "Do you offer custom designs?",
        "answer": "Yes, we offer bespoke custom design services. You can contact our support team to schedule a virtual consultation with our lead designers."
    },
    {
        "question": "What is your return policy?",
        "answer": "We offer a 7-day hassle-free return policy on standard catalog items. Custom-designed pieces cannot be returned once production begins."
    },
    {
        "question": "How do I contact support?",
        "answer": "Fill out the contact form on this page or use the live chat assistant widget in the bottom-right corner for quick responses."
    }
]

def ensure_faqs_seeded():
    try:
        faqs = FAQModel.find_all()
        if not faqs:
            for item in DEFAULT_FAQS:
                FAQModel.create_faq(item["question"], item["answer"])
    except Exception as e:
        print("Failed to seed FAQs:", e)

@support_bp.route('', methods=['POST'])
def submit_contact_form():
    data = request.get_json() or {}
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    message = str(data.get("message") or "").strip()
    
    if not all([name, email, message]):
        return jsonify({"message": "Please provide your name, email, and message."}), 400

    # Determine user_id if user is authenticated or by email lookup
    user_id = None
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header:
        try:
            token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else auth_header
            from backend.middleware.auth import decode_jwt_token
            decoded_data, err = decode_jwt_token(token)
            if decoded_data and isinstance(decoded_data, dict):
                uid_val = decoded_data.get("user_id") or decoded_data.get("id")
                if uid_val and str(uid_val).isdigit():
                    user_id = int(uid_val)
        except Exception:
            pass

    if not user_id and email:
        from backend.models.user import UserModel
        user_obj = UserModel.query.filter(
            (UserModel.email == email) | (UserModel.email == email.lower())
        ).first()
        if user_obj:
            user_id = user_obj.id

    msg = SupportModel.create_message(name, email, message, user_id=user_id)
    if not msg:
        return jsonify({"message": "We could not create your support ticket. Please try again."}), 500

    return jsonify({
        "message": "Thank you! Your support message has been submitted. Our team will contact you shortly.",
        "support_message": msg
    }), 201


@support_bp.route('/<int:ticket_id>/reply', methods=['POST'])
@token_required
def reply_to_ticket(current_user, ticket_id):
    from backend.models.support import SupportModel, SupportReplyModel
    from backend.models.user import UserModel
    from backend.routes.auth import add_user_notification
    from backend.utils.email_service import send_support_ticket_reply
    from backend.extensions import db
    
    try:
        ticket = SupportModel.query.with_for_update().get(ticket_id)
        if not ticket:
            return jsonify({"message": "Support ticket not found."}), 404
        caller_id_value = current_user.get("id") or current_user.get("_id")
        if not caller_id_value or not str(caller_id_value).isdigit():
            return jsonify({"message": "Invalid authenticated user."}), 401
        caller_id = int(caller_id_value)
        caller_is_admin = bool(current_user.get("is_admin"))
        if not caller_is_admin and ticket.user_id != caller_id:
            return jsonify({"message": "Access denied."}), 403
            
        data = request.get_json() or {}
        # Do not trust a client-provided sender label to impersonate support staff.
        sender = "Admin Support" if caller_is_admin else (current_user.get("name") or ticket.name or "Customer")
        message = str(data.get("message") or "").strip()
        
        if not message:
            return jsonify({"message": "Message is required."}), 400
            
        reply = SupportReplyModel(
            support_id=ticket.id,
            sender=sender,
            message=message
        )
        db.session.add(reply)
        
        is_admin_reply = caller_is_admin
        
        email_delivery = {"success": False, "status": "not_applicable"}
        if is_admin_reply:
            ticket.status = "Replied"
        else:
            # A customer response needs support attention again.
            ticket.status = "Pending"
            
        db.session.commit()
        
        # Trigger Notifications: Notify ticket owner ONLY if admin replied
        if is_admin_reply:
            recipient_user = None
            if ticket.user_id:
                recipient_user = UserModel.query.get(int(ticket.user_id))
            if not recipient_user and ticket.email:
                recipient_user = UserModel.query.filter(
                    (UserModel.email == ticket.email) | (UserModel.email == ticket.email.lower())
                ).first()
                if recipient_user:
                    ticket.user_id = recipient_user.id
                    db.session.commit()
                    
            if recipient_user:
                add_user_notification(
                    user_id=recipient_user.id,
                    title="Support Ticket Reply",
                    message=message,
                    notif_type="support_ticket_reply",
                    ticket_id=ticket.id,
                    original_message=ticket.message
                )

            recipient_email = getattr(recipient_user, "email", None) if recipient_user else ticket.email
            recipient_name = getattr(recipient_user, "full_name", None) if recipient_user else ticket.name
            if recipient_email:
                email_delivery = send_support_ticket_reply(
                    recipient_email,
                    recipient_name,
                    ticket.id,
                    ticket.message,
                    message,
                )
            else:
                email_delivery = {"success": False, "status": "no_recipient"}
        
        return jsonify({
            "message": "Reply submitted successfully!",
            "reply": reply.to_dict(),
            "success": True,
            "email_sent": email_delivery.get("status") == "delivered" if is_admin_reply else False,
            "email_status": email_delivery.get("status")
        }), 201
    except Exception as e:
        db.session.rollback()
        print("Failed to save support ticket reply:", e)
        return jsonify({"message": f"Failed to reply: {str(e)}"}), 500

@support_bp.route('/my-tickets', methods=['GET'])
@token_required
def get_my_tickets(current_user):
    user_id = current_user.get("_id") or current_user.get("id")
    email = str(current_user.get("email") or "").strip().lower()
    if not user_id and not email:
        return jsonify([]), 200
    
    from sqlalchemy.orm import selectinload
    from sqlalchemy import or_
    
    conditions = []
    if user_id and str(user_id).isdigit():
        conditions.append(SupportModel.user_id == int(user_id))
    if email:
        conditions.append(SupportModel.email == email)
        conditions.append(SupportModel.email == email.lower())
        
    if not conditions:
        return jsonify([]), 200

    query = SupportModel.query.options(selectinload(SupportModel.replies)).filter(or_(*conditions)).order_by(SupportModel.created_at.desc())
    
    page_arg = request.args.get('page')
    limit_arg = request.args.get('limit') or request.args.get('page_size')
    if page_arg or limit_arg or request.args.get('paginate') == 'true':
        from backend.utils.pagination import parse_pagination_params, paginate_query
        p_num, p_limit = parse_pagination_params()
        return jsonify(paginate_query(query, page=p_num, limit=p_limit)), 200

    tickets = query.all()
    return jsonify([t.to_dict() for t in tickets]), 200


@support_bp.route('/all', methods=['GET'])
@admin_required
def get_all_messages():
    page_arg = request.args.get('page')
    limit_arg = request.args.get('limit') or request.args.get('page_size')
    if page_arg or limit_arg or request.args.get('paginate') == 'true':
        from backend.utils.pagination import parse_pagination_params
        p_num, p_limit = parse_pagination_params()
        messages = SupportModel.find_all(page=p_num, limit=p_limit)
        return jsonify(messages), 200
    messages = SupportModel.find_all()
    return jsonify(messages), 200

@support_bp.route('/faqs', methods=['GET'])
def get_faqs():
    ensure_faqs_seeded()
    faqs = FAQModel.find_all()
    return jsonify([f.to_dict() for f in faqs]), 200

@support_bp.route('/faqs', methods=['POST'])
@admin_required
def add_faq():
    data = request.get_json() or {}
    question = data.get("question")
    answer = data.get("answer")
    if not question or not answer:
        return jsonify({"message": "Question and Answer are required."}), 400
    faq = FAQModel.create_faq(question, answer)
    if faq:
        from backend.utils.audit import log_admin_action
        log_admin_action("Support Ticket Updated", "Support Management", f"Added new FAQ: '{question}'")
        return jsonify(faq), 201
    return jsonify({"message": "Failed to create FAQ."}), 500

@support_bp.route('/faqs/<int:faq_id>', methods=['PUT'])
@admin_required
def update_faq(faq_id):
    data = request.get_json() or {}
    question = data.get("question")
    answer = data.get("answer")
    if not question or not answer:
        return jsonify({"message": "Question and Answer are required."}), 400
    faq = FAQModel.update_faq(faq_id, question, answer)
    if faq:
        from backend.utils.audit import log_admin_action
        log_admin_action("Support Ticket Updated", "Support Management", f"Updated FAQ ID {faq_id}: '{question}'")
        return jsonify(faq), 200
    return jsonify({"message": "FAQ not found or update failed."}), 404

@support_bp.route('/faqs/<int:faq_id>', methods=['DELETE'])
@admin_required
def delete_faq(faq_id):
    success = FAQModel.delete_faq(faq_id)
    if success:
        from backend.utils.audit import log_admin_action
        log_admin_action("Support Ticket Updated", "Support Management", f"Deleted FAQ ID {faq_id}")
        return jsonify({"message": "FAQ deleted successfully."}), 200
    return jsonify({"message": "FAQ not found or delete failed."}), 404

@support_bp.route('/messages/<int:msg_id>/status', methods=['PUT'])
@admin_required
def update_message_status(msg_id):
    from backend.extensions import db
    data = request.get_json() or {}
    status = data.get("status")
    if not status:
        return jsonify({"message": "Status is required."}), 400
        
    try:
        msg = SupportModel.query.with_for_update().get(msg_id)
        if not msg:
            return jsonify({"message": "Message not found."}), 404
            
        old_status = msg.status
        msg.status = status
        db.session.commit()
        
        # Audit Log
        try:
            from backend.utils.audit import log_admin_action
            log_admin_action("Support Ticket Updated", "Support Management", f"Updated support ticket status from '{old_status}' to '{status}' for message from '{msg.name}' (ID: {msg_id})")
        except Exception as ex:
            print("Failed to log admin action:", ex)
        
        return jsonify({"message": "Support message status updated successfully.", "status": status}), 200
    except Exception as e:
        db.session.rollback()
        print("Error updating support message status:", e)
        return jsonify({"message": "An error occurred while updating support message status."}), 500

DEFAULT_SUPPORT_LINKS = [
    {
        "title": "+91 98765 43210",
        "url": "tel:+919876543210",
        "icon": "Phone"
    },
    {
        "title": "support@SSJewellery.com",
        "url": "mailto:support@SSJewellery.com",
        "icon": "Mail"
    },
    {
        "title": "Connaught Place, New Delhi, India",
        "url": "https://maps.google.com/?q=Connaught+Place,+New+Delhi,+India",
        "icon": "MapPin"
    }
]

def ensure_support_links_seeded():
    try:
        links = SupportLinkModel.find_all()
        if not links:
            for item in DEFAULT_SUPPORT_LINKS:
                SupportLinkModel.create_link(item["title"], item["url"], item["icon"])
    except Exception as e:
        print("Failed to seed support links:", e)

@support_bp.route('/links', methods=['GET'])
def get_support_links():
    links = SupportLinkModel.find_all()
    response = jsonify([link.to_dict() for link in links])
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@support_bp.route('/links', methods=['POST'])
@admin_required
def add_support_link():
    data = request.get_json() or {}
    title = str(data.get("title") or "").strip()
    url = str(data.get("url") or "").strip()
    icon = str(data.get("icon") or "Phone").strip()
    is_active = data.get("is_active", True)
    if not title or not url:
        return jsonify({"message": "Title and URL are required."}), 400
    if not _is_valid_support_url(url):
        return jsonify({"message": "Use a valid https://, http://, mailto:, tel:, or internal / link."}), 400
    link = SupportLinkModel.create_link(title, url, icon, is_active)
    if link:
        from backend.utils.audit import log_admin_action
        log_admin_action("Support Ticket Updated", "Support Management", f"Added new Support Link: '{title}' ({url})")
        return jsonify(link), 201
    return jsonify({"message": "Failed to create support link."}), 500

@support_bp.route('/links/<int:link_id>', methods=['PUT'])
@admin_required
def update_support_link(link_id):
    data = request.get_json() or {}
    title = str(data.get("title") or "").strip()
    url = str(data.get("url") or "").strip()
    icon = str(data.get("icon") or "").strip()
    is_active = data.get("is_active", True)
    if not title or not url or not icon:
        return jsonify({"message": "Title, URL, and Icon are required."}), 400
    if not _is_valid_support_url(url):
        return jsonify({"message": "Use a valid https://, http://, mailto:, tel:, or internal / link."}), 400
    link = SupportLinkModel.update_link(link_id, title, url, icon, is_active)
    if link:
        from backend.utils.audit import log_admin_action
        log_admin_action("Support Ticket Updated", "Support Management", f"Updated Support Link ID {link_id}: '{title}'")
        return jsonify(link), 200
    return jsonify({"message": "Support link not found or update failed."}), 404

@support_bp.route('/links/<int:link_id>', methods=['DELETE'])
@admin_required
def delete_support_link(link_id):
    success = SupportLinkModel.delete_link(link_id)
    if success:
        from backend.utils.audit import log_admin_action
        log_admin_action("Support Ticket Updated", "Support Management", f"Deleted Support Link ID {link_id}")
        return jsonify({"message": "Support link deleted successfully."}), 200
    return jsonify({"message": "Support link not found or delete failed."}), 404



