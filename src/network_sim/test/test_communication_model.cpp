#include <gtest/gtest.h>
#include "network_sim/log_distance_model.hpp"
#include "network_sim/congestion_aware_model.hpp"

using namespace network_sim;

class LogDistanceModelTest : public ::testing::Test {
protected:
  LogDistanceModel model{20.0, 2.5, 1.0, 40.0, 50.0, 20.0, 2.0, 0.5};
};

TEST_F(LogDistanceModelTest, Name) {
  EXPECT_EQ(model.get_model_name(), "Log-Distance Path Loss Model");
}

TEST_F(LogDistanceModelTest, ZeroDistance) {
  auto q = model.calculate(0.001, 1);
  EXPECT_NEAR(q.rssi_dbm, 20.0 - 40.0, 1.0);
  EXPECT_NEAR(q.packet_loss_rate, 0.0, 0.01);
}

TEST_F(LogDistanceModelTest, ShortRangeExcellent) {
  auto q = model.calculate(5.0, 1);
  EXPECT_GT(q.rssi_dbm, -60.0) << "RSSI should be excellent at short range";
  EXPECT_EQ(q.packet_loss_rate, 0.0);
}

TEST_F(LogDistanceModelTest, MediumRangeDegradation) {
  auto q = model.calculate(100.0, 1);
  EXPECT_LT(q.rssi_dbm, -60.0);
  EXPECT_GT(q.rssi_dbm, -90.0);
  EXPECT_GT(q.packet_loss_rate, 0.0);
  EXPECT_LT(q.packet_loss_rate, 1.0);
}

TEST_F(LogDistanceModelTest, LongRangePoor) {
  auto q = model.calculate(5000.0, 1);
  EXPECT_LT(q.rssi_dbm, -90.0);
  EXPECT_EQ(q.packet_loss_rate, 1.0);
}

TEST_F(LogDistanceModelTest, LatencyIncreasesWithDistance) {
  auto q1 = model.calculate(10.0, 1);
  auto q2 = model.calculate(1000.0, 1);
  EXPECT_GT(q2.latency_ms, q1.latency_ms);
}

TEST_F(LogDistanceModelTest, JitterIncreasesWithLoss) {
  auto q1 = model.calculate(10.0, 1);
  auto q2 = model.calculate(5000.0, 1);
  EXPECT_GT(q2.jitter_ms, q1.jitter_ms);
}

TEST_F(LogDistanceModelTest, PathLossFormula) {
  auto q = model.calculate(100.0, 1);
  double expected_pl = 40.0 + 10.0 * 2.5 * log10(100.0);
  EXPECT_NEAR(q.path_loss_db, expected_pl, 0.1);
}

TEST_F(LogDistanceModelTest, RSSICalculation) {
  auto q = model.calculate(100.0, 1);
  double expected_pl = 40.0 + 10.0 * 2.5 * log10(100.0);
  EXPECT_NEAR(q.rssi_dbm, 20.0 - expected_pl, 0.1);
}

TEST_F(LogDistanceModelTest, MultipleVehicles) {
  auto q = model.calculate(100.0, 5);
  EXPECT_EQ(q.vehicles_in_range, 5);
}

// Test with different path loss exponents
TEST_F(LogDistanceModelTest, DifferentPathLossExponents) {
  LogDistanceModel free_space(20.0, 2.0, 1.0, 40.0, 50.0, 20.0, 2.0, 0.5);
  LogDistanceModel urban(20.0, 3.5, 1.0, 40.0, 50.0, 20.0, 2.0, 0.5);

  auto q_free = free_space.calculate(100.0, 1);
  auto q_urban = urban.calculate(100.0, 1);

  EXPECT_GT(q_urban.path_loss_db, q_free.path_loss_db);
  EXPECT_LT(q_urban.rssi_dbm, q_free.rssi_dbm);
}

// Congestion-aware model tests
TEST(CongestionModelTest, LowCongestion) {
  CongestionAwareModel model(20.0, 2.5, 1.0, 40.0, 50.0, 20.0, 2.0, 0.5);
  auto q = model.calculate(100.0, 2);
  EXPECT_GT(q.latency_ms, 0);
  EXPECT_GE(q.packet_loss_rate, 0);
  EXPECT_LE(q.packet_loss_rate, 1);
}

TEST(CongestionModelTest, HighCongestionIncreasesLatency) {
  CongestionAwareModel model(20.0, 2.5, 1.0, 40.0, 50.0, 20.0, 2.0, 0.5);
  auto q_low = model.calculate(100.0, 2);
  auto q_high = model.calculate(100.0, 20);
  EXPECT_GT(q_high.latency_ms, q_low.latency_ms);
}

int main(int argc, char **argv) {
  testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
