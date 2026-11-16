# v157.3 export monitoring/scorecard regression alignment

The v157.2 export enhancements added historical revision rows to the shared scorecard. An old monitoring regression asserted exactly six scorecard rows, even though the correct rows now include additional historical metrics. Updated test to assert the monitoring value and revision-history presence instead of a fixed scorecard length. All business logic from v157.2 is unchanged. No database writes or migrations.
