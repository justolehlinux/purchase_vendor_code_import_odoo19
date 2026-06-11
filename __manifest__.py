{
    "name": "Purchase Import by Vendor Product Code",
    "summary": "Import purchase order products by vendor code and safely remove exact vendor pricelist duplicates",
    "version": "19.0.1.3.0",
    "category": "Purchases",
    "author": "Bravo Market",
    "license": "LGPL-3",
    "depends": ["purchase"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/supplierinfo_deduplicate_wizard_views.xml",
        "data/supplierinfo_actions.xml",
    ],
    "installable": True,
    "application": False,
}
