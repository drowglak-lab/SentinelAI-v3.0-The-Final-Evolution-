package sentinel.fintech

# Включаем современный синтаксис (Rego v1)
import rego.v1

# Запрещаем всё по умолчанию
default allow := false

# Разрешаем перевод только если выполняются ВСЕ условия
allow if {
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
is_sanctioned(country) if {
    sanctioned_countries := {"NK", "IR", "SY"}
    country in sanctioned_countries
}
