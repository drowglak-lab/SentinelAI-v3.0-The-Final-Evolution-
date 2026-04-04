use pyo3::prelude::*;
use std::sync::Arc;
use arc_swap::ArcSwap;

mod models;
mod store;
mod engine;

// Глобальное хранилище, которое будет жить в памяти на протяжении работы Python-процесса
lazy_static::lazy_static! {
    static ref GLOBAL_STORE: store::PolicyStore = store::PolicyStore::new_empty();
}

#[pymodule]
fn sentinel_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<models::Decision>()?;
    m.add_class::<models::EvaluationResult>()?;
    
    // Функция для наполнения хранилища политиками из Python
    #[pyfn(m)]
    #[pyo3(name = "add_policy")]
    fn add_policy(id: String, tool_name: String, priority: u32) -> PyResult<()> {
        let policy = Arc::new(models::Policy { id, tool_name, priority });
        GLOBAL_STORE.raw_store.insert(policy.id.clone(), policy);
        
        // Пересобираем Snapshot для обеспечения O(1) доступа в горячем цикле
        GLOBAL_STORE.rebuild_snapshot();
        Ok(())
    }

    // Основная точка входа для высокоскоростной оценки
    #[pyfn(m)]
    #[pyo3(name = "fast_evaluate")]
    fn fast_evaluate(tool_name: &str, risk: f32) -> PyResult<models::EvaluationResult> {
        // 1. Загружаем текущий снимок реальности (lock-free)
        let snapshot = GLOBAL_STORE.snapshot.load_full();
        
        // 2. Инициализируем движок этим снимком
        let engine = engine::EvaluationEngine { snapshot };
        
        // 3. Выполняем реальную проверку по алгоритму Deny-Overrides
        Ok(engine.evaluate(tool_name, risk))
    }

    Ok(())
}
