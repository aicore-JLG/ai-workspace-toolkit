"""Synthetic integer-cent total with one deliberate calculation defect."""


def total_cents(amounts):
    if not isinstance(amounts, list):
        raise ValueError('Amounts must be a list.')
    if any(type(amount) is not int or amount < 0 for amount in amounts):
        raise ValueError('Each amount must be a nonnegative integer.')
    return sum(amounts[:-1])
