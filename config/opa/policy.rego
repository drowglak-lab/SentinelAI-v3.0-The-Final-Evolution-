package sentinel.fintech

# Запрещаем всё по умолчанию (Deny by default - золотое правило финтеха)
default allow = false

# Разрешаем перевод только если выполняются ВСЕ условия
allow {
    input.action == "transfer_funds"
    
    # Проверка лимитов
    input.amount > 0
    input.amount <= 50000
    
    # Проверка рисков (Semantic checks)
    input.beneficiary.is_active == 1
    input.beneficiary.aml_risk_score < 80
    
    # Санкционный контроль
    not is_sanctioned(input.beneficiary.country_code)
}

# Вспомогательное правило: список санкционных стран
is_sanctioned(country) {
    sanctioned_countries := {"NK", "IR", "SY"}
    country == sanctioned_countries[_]
}
