"""Base models."""
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OwnerlessAbstractBase(models.Model):
    """Abstract base model without an owner (library)."""

    _name = "ownerless.abstract.base"
    _description = "Shared model by all business objects."
    _abstract = True

    guid = fields.Char(
        copy=False, readonly=True, default=lambda self: self._guid()
    )
    active = fields.Boolean(default=True)

    def guid(self):
        """System generated guid."""
        return uuid.uuid4()


class AbstractBase(models.Model):
    """Abstract base with an owner."""

    _name = "abstract.base"
    _description = "Shared model by all business objects."
    _abstract = True
    _inherit = ["ownerless.abstract.base"]

    library = fields.Many2one(
        "library",
        ondelete="restrict",
        readonly=True,
        domain=lambda self: self._library_user_domain(),
    )

    def _current_user_domain(self):
        """Current user search domain."""
        user_id = self.env.user.id
        return [("id", "=", user_id)]

    def _current_user(self):
        """Get the current logged in user."""
        user = self.env["res.users"].search(self._current_user_domain())
        return user

    def _library_user_domain(self):
        """Library search/read domain."""
        user = self._current_user()
        return [
            ("user", "=", user.id),
            ("active", "=", True),
        ]

    def current_library(self):
        """Get the assigned library for the current user."""
        library = self.env["library"].search(self._library_user_domain())

        if not library:
            raise ValidationError(
                _(
                    "The current user in session is not assigned "
                    "to a library or assigned to an inactive library"
                )
            )

        if len(library) > 1:
            raise ValidationError(
                _("The current user is assigned to more than one library.")
            )

        return library

    @api.model
    def create(self, vals):
        """Override create method to add a library."""
        library = self.current_library()
        if not vals.get("library"):
            vals["library"] = library.id

        return super(AbstractBase, self).create(vals)
