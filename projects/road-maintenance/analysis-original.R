# Original R code extracted from the submitted coursework HTML.
# Not rerun; requires pavement.csv, which is not included.

install.packages("shiny")

library(shiny)
library(readr)
data <- read_csv("pavement.csv")

install.packages("patchwork") 

library(patchwork)
install.packages("tidyverse")

library(tidyverse)
install.packages("tidytext")  

library(tidytext)
install.packages("yardstick")

install.packages("caret")

glimpse(data)         

summary(data)         

library(tibble)

var_def <- tribble(
  ~變數名稱,         ~類型,               ~說明,
  "Needs Maintenance", "目標變數（0/1）",  "是否需要維修（1=需要）",
  "PCI",               "連續變數",         "鋪面狀況指數",
  "IRI",               "連續變數",         "國際平坦度指數",
  "Rutting",           "連續變數",         "車轍深度",
  "AADT",              "連續變數",         "年平均每日交通量",
  "Average Rainfall",  "連續變數",         "平均年雨量",
  "Last Maintenance",  "整數（年份）",     "最後維修年份",
  "Road Type",         "類別變數",         "道路型別",
  "Asphalt Type",      "類別變數",         "鋪面材質"
)
var_def

ggplot(data, aes(x = Rutting, y = IRI, color = factor(`Needs Maintenance`))) +
  geom_point(alpha = 0.4) +
  labs(x = "Rutting", y = " IRI", color = "need maintenance or not",
       title = "Rutting v.s IRI ") +
  theme_light()

ggplot(data, aes(x = PCI, y = AADT, color = factor(`Needs Maintenance`))) +
  geom_point(alpha = 0.4) +
  labs(x = "PCI", y = "AADT", color = "need maintenance",
       title = "PCI v.s AADT") +
  theme_light()

library(ggplot2)

ggplot(data, aes(x = Rutting, y = `Average Rainfall`, color = factor(`Needs Maintenance`))) +
  geom_point(alpha = 0.3) +
  labs(
    title = "Rutting v.s Average Rainfall ",
    x = " Rutting",
    y = "Average Rainfall",
    color = "need maintenance"
  ) +
  scale_color_manual(values = c("0" = "#FF6F61", "1" = "#00BFC4")) +
  theme_minimal()

install.packages("patchwork")   

library(patchwork)            
# 圖1：AADT vs PCI
plot1 <- ggplot(data, aes(x = AADT, y = PCI)) +
  geom_point(alpha = 0.3, color = "steelblue") +
  facet_wrap(~ `Needs Maintenance`) +
  labs(title = "AADT vs PCI", x = "AADT", y = "PCI") +
  theme_minimal()

# 圖2：Rainfall vs PCI
plot2 <- ggplot(data, aes(x = `Average Rainfall`, y = PCI)) +
  geom_point(alpha = 0.3, color = "MediumAquamarine") +
  facet_wrap(~ `Needs Maintenance`) +
  labs(title = "Rainfall vs PCI", x = "Average Rainfall", y = "PCI") +
  theme_minimal()

# 圖3：Last Maintenance vs PCI
plot3 <- ggplot(data, aes(x = `Last Maintenance`, y = PCI)) +
  geom_point(alpha = 0.3, color = "purple") +
  facet_wrap(~ `Needs Maintenance`) +
  labs(title = "Last time maintenance vs PCI", x = "Last Maintenance", y = "PCI") +
  theme_minimal()

plot1 / plot2 / plot3

library(ggplot2)
library(dplyr)
library(tidytext) 

data |>
  group_by(`Road Type`, `Needs Maintenance`) |>
  summarise(count = n(), .groups = "drop") |>
  mutate(pct = count / sum(count)) |>
  mutate(road_sorted = reorder_within(`Road Type`, pct, `Needs Maintenance`)) |>
  ggplot(aes(x = road_sorted, y = pct, fill = factor(`Needs Maintenance`))) +
  geom_col(show.legend = FALSE) +
  facet_wrap(~ `Needs Maintenance`, scales = "free_x") +
  scale_x_reordered() + 
  scale_y_continuous(labels = scales::percent_format()) +
  labs(
    x = "Road Type",
    y = "propotion",
    title = "Road Type urder different maintenance situation",
    fill = "Needs Maintenance or not"
  ) +
  theme_minimal()

data_asphalt <- data |>
  group_by(`Asphalt Type`, `Needs Maintenance`) |>
  summarise(n = n(), .groups = "drop") |>
  group_by(`Needs Maintenance`) |>
  mutate(proportion = n / sum(n)) |>
  mutate(Asphalt_Sorted = reorder_within(`Asphalt Type`, proportion, `Needs Maintenance`))

ggplot(data_asphalt, aes(x = Asphalt_Sorted, y = proportion, fill = factor(`Needs Maintenance`))) +
  geom_col(show.legend = FALSE) +
  facet_wrap(~ `Needs Maintenance`, scales = "free_x") +
  scale_x_reordered() +
  scale_y_continuous(labels = scales::percent_format()) +
  labs(
    title = "Asphalt Type under Different Maintenance Situation",
    x = "Asphalt Type",
    y = "proportion"
  ) +
  theme_minimal()

# --- Road Type 視覺化 ---
data_road <- data |>
  group_by(`Road Type`, `Needs Maintenance`) |>
  summarise(n = n(), .groups = "drop") |>
  group_by(`Needs Maintenance`) |>
  mutate(proportion = n / sum(n)) |>
  mutate(Road_Sorted = reorder_within(`Road Type`, proportion, `Needs Maintenance`))

plot_road <- ggplot(data_road, aes(x = Road_Sorted, y = proportion, fill = factor(`Needs Maintenance`))) +
  geom_col(show.legend = FALSE) +
  facet_wrap(~ `Needs Maintenance`, scales = "free_x") +
  scale_x_reordered() +
  scale_y_continuous(labels = scales::percent_format()) +
  labs(
    title = "Order with Road Type and propotion",
    x = "Road Type",
    y = "Propotion"
  ) +
  theme_minimal()

# --- Asphalt Type 視覺化 ---
data_asphalt <- data |>
  group_by(`Asphalt Type`, `Needs Maintenance`) |>
  summarise(n = n(), .groups = "drop") |>
  group_by(`Needs Maintenance`) |>
  mutate(proportion = n / sum(n)) |>
  mutate(Asphalt_Sorted = reorder_within(`Asphalt Type`, proportion, `Needs Maintenance`))

plot_asphalt <- ggplot(data_asphalt, aes(x = Asphalt_Sorted, y = proportion, fill = factor(`Needs Maintenance`))) +
  geom_col(show.legend = FALSE) +
  facet_wrap(~ `Needs Maintenance`, scales = "free_x") +
  scale_x_reordered() +
  scale_y_continuous(labels = scales::percent_format()) +
  labs(
    title = "Order with Asphalt Type propotion",
    x = "Asphalt Type",
    y = "propotion"
  ) +
  theme_minimal()

plot_road / plot_asphalt

data_predict <- data |>
  filter(!is.na(`Last Maintenance`)) |>
  group_by(`Last Maintenance`) |>
  summarise(rate = mean(`Needs Maintenance`), .groups = "drop")

ggplot(data_predict, aes(x = `Last Maintenance`, y = rate)) +
  geom_line(color = "darkred", size = 1) +
  geom_point() +
  scale_y_continuous(labels = scales::percent_format()) +
  labs(
    title = "",
    x = "Last Maintenance ",
    y = "Maintenance Rate"
  ) +
  theme_minimal()

install.packages("ggcorrplot")

library(ggcorrplot)
# 篩選數值變數，包含目標變數 Needs Maintenance
num_vars <- data[, c("Needs Maintenance", "PCI", "IRI", "Rutting", "AADT", "Average Rainfall", "Last Maintenance")]

# 計算皮爾森相關係數
cor_matrix <- cor(num_vars, use = "complete.obs")

ggcorrplot(
  cor_matrix,
  method = "square",           
  type = "lower",              
  lab = TRUE,                 
  lab_size = 3,
  colors = c("SkyBlue", "DodgerBlue", "Blue"),
  title = "Correlation between variables anr Needs Maintenance ",
  ggtheme = theme_minimal()
)

# 年份分組
data <- data |>
  mutate(MaintPeriod = cut(`Last Maintenance`, breaks = seq(1980, 2025, by = 5), right = FALSE))

# 熱度資料框建立
data_heat <- data |>
  filter(!is.na(PCI) & !is.na(Rutting) & !is.na(MaintPeriod)) |>
  mutate(
    PCI_bin = cut(PCI, breaks = seq(0, 100, by = 10), include.lowest = TRUE),
    Rutting_bin = cut(Rutting, breaks = seq(0, ceiling(max(Rutting, na.rm = TRUE)), by = 5), include.lowest = TRUE)
  ) |>
  group_by(PCI_bin, Rutting_bin, MaintPeriod) |>
  summarise(
    NeedsRate = mean(`Needs Maintenance`),
    n = n(), .groups = "drop"
  ) |>
  filter(n >= 10)


ggplot(data_heat, aes(x = PCI_bin, y = Rutting_bin, fill = NeedsRate)) +
  geom_tile(color = "white") +
  facet_wrap(~ MaintPeriod) +
  scale_fill_gradient(low = "white", high = "darkred", labels = scales::percent) +
  labs(
    title = "PCI × Rutting × Last Maintenance",
    x= "PCI by group",
    y = "Rutting by group",
    fill = "Maintenance Rate"
  ) +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

var_table <- tribble(
  ~"變數名稱",                     ~"解釋",                   ~"權重（預設）",
  "`PCI`（鋪面狀況指數）",            "數值越低代表越破",         "負相關，權重 `-0.5`",
  "`Rutting`（車轍深度）",          "數值越高代表越凹陷嚴重",   "正相關，權重 `+0.3`",
  "`Average Rainfall`（平均降雨）", "降雨多代表風險高",         "正相關，權重 `+0.2`"
)

#Priority_Score = -0.5 * PCI + 0.3 *Rutting + 0.2 * Average Rainfall
#前面係數為根據上個部分分析結果所假設
library(tidyverse)


# 建立排序指數
data_priority <- data |>
  filter(!is.na(PCI) & !is.na(Rutting) & !is.na(`Average Rainfall`)) |>
  mutate(
    Priority_Score = -0.5 * PCI + 0.3 * Rutting + 0.2 * `Average Rainfall`
  ) |>
  arrange(desc(Priority_Score))  # 高分排前面
data_priority |>
  slice_max(Priority_Score, n = 20) |>
  ggplot(aes(x = reorder(`Segment ID`, Priority_Score), y = Priority_Score)) +
  geom_col(fill = "Salmon") +
  coord_flip() +
  labs(title = "order with priority score",
       x = "Road ID", y = "priority score") +
  theme_minimal()

library(tidyverse)
library(broom)
library(ggplot2)


model_data <- data %>%
  select(`Needs Maintenance`, PCI, Rutting, IRI, AADT, `Average Rainfall`, `Last Maintenance`) %>%
  drop_na()


logit_model <- glm(`Needs Maintenance` ~ ., data = model_data, family = "binomial")

summary(logit_model)

coef_df <- tidy(logit_model) %>%
  filter(term != "(Intercept)") %>%
  mutate(term = reorder(term, estimate)) 


ggplot(coef_df, aes(x = term, y = estimate)) +
  geom_col(fill = "steelblue") +
  geom_text(aes(label = round(estimate, 2)), hjust = ifelse(coef_df$estimate > 0, -0.1, 1.1)) +
  coord_flip() +
  labs(
    title = "Logistic Regression Order",
    x = "Variable",
    y = "Estimate"
  ) +
  theme_minimal()

coef_df

summary(logit_model)
