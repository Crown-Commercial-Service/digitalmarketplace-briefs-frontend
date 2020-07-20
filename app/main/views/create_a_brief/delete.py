from flask import abort, flash, redirect, url_for
from flask_login import current_user

from app import data_api_client
from ... import main
from ...helpers.buyers_helpers import (
    brief_can_be_edited,
    get_framework_and_lot,
    is_brief_correct,
)


BRIEF_DELETED_MESSAGE = "Your requirements ‘{brief[title]}’ were deleted"


@main.route('/frameworks/<framework_slug>/requirements/<lot_slug>/<brief_id>/delete', methods=['POST'])
def delete_a_brief(framework_slug, lot_slug, brief_id):
    get_framework_and_lot(
        framework_slug,
        lot_slug,
        data_api_client,
        allowed_statuses=['live', 'expired'],
        must_allow_brief=True
    )
    brief = data_api_client.get_brief(brief_id)["briefs"]

    if not is_brief_correct(brief, framework_slug, lot_slug, current_user.id) or not brief_can_be_edited(brief):
        abort(404)

    data_api_client.delete_brief(brief_id, current_user.email_address)
    flash(BRIEF_DELETED_MESSAGE.format(brief=brief), "success")

    return redirect(url_for(".buyer_dos_requirements"))
