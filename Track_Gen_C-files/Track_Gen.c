/*
 * IFF_Flight_Track_Gen.c
 *
 *  Created on: Aug 4, 2020
 *      Author: eknobloc
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#pragma warning(disable : 4996)
#pragma warning(disable : 4703)

#define	TRK_RECORD_TYPE		1
#define	TRK_TIME_STAMP		2
#define	TRK_RECORD_KEY		3
#define	TRK_AC_ID			8
#define	TRK_AC_LAT			10
#define	TRK_AC_LONG			11
#define	TRK_AC_ALT			12
#define	TRK_AC_GND_SPD		17
#define	TRK_AC_COURSE		18
#define	TRK_RATE_CLIMB		19

#define	SUM_RECORD_KEY		3
#define	SUM_AC_ID			8
#define	SUM_ORIG			11
#define	SUM_DEST			12

#define PLAN_WAYPOINTS		18

#define	FLIGHT_SUMMARY		'2'
#define	TRACK_POINT			'3'
#define	FLIGHT_PLAN			'4'

// This function searches through character array s, and retrieves a character array t, based on the provided
// delimiter character and position.
void get_token(char *s, char *t, char delim, int position, int MAX_LEN) {
	int i = 0, j = 0;
	int delim_cnt = 0;

	for(i=0; i<MAX_LEN; i++) {
		if(s[i] == delim)
			delim_cnt++;

		if(delim_cnt == position - 1)
			if(s[i] != delim)
				t[j++] = s[i];
	}
	t[j] = '\0';
	if(!strcmp(t, "?"))
		strcpy(t, "Unknown");
	//if(position == PLAN_WAYPOINTS) {printf("%s",t);}
}

void write_kml_header(FILE *fp) {
	fprintf(fp, "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
	fprintf(fp, "<kml xmlns=\"http://www.opengis.net/kml/2.2\">\n");
	fprintf(fp, "  <Document>\n");
	fprintf(fp, "    <name>Paths</name>\n");
	fprintf(fp, "    <description> Flight path of aircraft. </description>\n");
	fprintf(fp, "    <Style id=\"yellowLineGreenPoly\">\n");
	fprintf(fp, "      <LineStyle>\n");
	fprintf(fp, "        <color>7f00ffff</color>\n");
	fprintf(fp, "        <width>4</width>\n");
	fprintf(fp, "      </LineStyle>\n");
	fprintf(fp, "      <PolyStyle>\n");
	fprintf(fp, "        <color>7f00ff00</color>\n");
	fprintf(fp, "      </PolyStyle>\n");
	fprintf(fp, "    </Style>\n");
	fprintf(fp, "    <Placemark>\n");
	fprintf(fp, "      <name>Absolute Extruded</name>\n");
	fprintf(fp, "      <description>Transparent green wall with yellow outlines</description>\n");
	fprintf(fp, "      <styleUrl>#yellowLineGreenPoly</styleUrl>\n");
	fprintf(fp, "      <LineString>\n");
	fprintf(fp, "        <extrude>1</extrude>\n");
	fprintf(fp, "        <tessellate>1</tessellate>\n");
	fprintf(fp, "        <altitudeMode>absolute</altitudeMode>\n");
	fprintf(fp, "        <coordinates>	");
}

void write_kml_footer(FILE *fp) {
	fprintf(fp, "        </coordinates>\n");
	fprintf(fp, "      </LineString>\n");
	fprintf(fp, "    </Placemark>\n");
	fprintf(fp, "  </Document>\n");
	fprintf(fp, "</kml>");
}

void close_and_exit(int code, FILE* fpsource,FILE *fpdest_track, FILE *fpdest_plan, FILE *fpdest_KML_track, FILE *fpdest_KML_plan, FILE *fpstatus) {
	if(fpsource != NULL){ fclose(fpsource); }
	if (fpdest_track != NULL) { fclose(fpdest_track); }
	if (fpdest_KML_track != NULL) { fclose(fpdest_KML_track); }
	if (fpdest_plan!= NULL) { fclose(fpdest_plan); }
	if (fpdest_KML_plan!= NULL) { fclose(fpdest_KML_plan); }
	if (fpstatus != NULL) { fclose(fpstatus); }
	exit(code);
}

int main() {
	FILE *fpsource, *fpdest_track, *fpdest_plan, *fpdest_KML_track, *fpdest_KML_plan, *fpstatus;
	int found_match = 0, track_point_count = 0, cnt = 0, flight_plan_count = 0;
	double alt_value = 0.0;
	char str[500], orig[20], dest[20], key[20];
	char ac_lat[20], ac_long[20], ac_alt[20], time_stamp[20], ac_id[20], ac_gnd_spd[20], ac_course[20], waypoints[200];
	char dest_path_track_point[200], dest_path_KML_flight_plan[200],dest_path_flight_plan[200], dest_path_KML_track_point[200];

	// Set the source file path
//	const char *source_path = "C:\\Users\\eknobloc\\Desktop\\Autonomous Spectrum Study\\Data Engineering\\IFF Flight Track\\IFF_Source.csv";
	const char *source_path = "C:\\Users\\natha\\Desktop\\IFF_Data\\IFF_USA_20190610_050000_86398.csv";

	// Set the status file path; this txt file provides a summary of what was found in the search. It includes the record number, origin airport, and destination airport
//	const char *status_path = "C:\\Users\\eknobloc\\Desktop\\Autonomous Spectrum Study\\Data Engineering\\IFF Flight Track\\IFF_Track_Summary.txt";
	const char *status_path = "C:\\Users\\natha\\Desktop\\IFF_Data\\2019-06-10\\IFF_Track_Summary.txt";

	// Set the output file path headers for the txt file and KML file; the file name will be appended with the origin airport, destination airport and aircraft ID
//	char dest_path_header[] = "C:\\Users\\eknobloc\\Desktop\\Autonomous Spectrum Study\\Data Engineering\\IFF Flight Track\\Flight_Track_";
	char dest_path_header[] = "C:\\Users\\natha\\Desktop\\IFF_Data\\2019-06-10\\Flight_Track";

	// Set the desired origin airport and desired destination airport; always include the terminating '\0' at the end of the string
	char desired_orig[] = "KJFK\0";
	char desired_dest[] = "KLAX\0";


	// Open source IFF source file; terminate if file error
	fpsource = fopen(source_path, "r");
	if(fpsource == NULL) {
		perror("Error opening source file");
		close_and_exit(-1, fpsource, NULL, NULL, NULL, NULL, NULL);
	}

	// Open the status file; terminate if file error
	fpstatus = fopen(status_path, "w");
	if(fpstatus == NULL) {
		perror("Error opening summary file");
		close_and_exit(-1, fpsource, NULL, NULL, NULL, NULL, fpstatus);
	}

	// Parse through IFF file to retrieve entries from the IFF CSV file (e.g., desired latitude, longitude, and altitude)
	// From those retrieve entries, generate an output string that contains those values and write to the destination file
	while(fgets(str, 200, fpsource) != NULL) {

		// Provide a status update on file processing
		if (++cnt % 10000 == 0)
			printf("Processing %d entries...\r", cnt);

		if(str[0] == FLIGHT_SUMMARY) {
			// New record has been found
			track_point_count = 0;
			flight_plan_count = 0;
			
			if(found_match == 1) {
				found_match = 0;
				fclose(fpdest_track);
				fclose(fpdest_plan);

				// write the footer text for the KML file
				write_kml_footer(fpdest_KML_track);
				fclose(fpdest_KML_track);
				write_kml_footer(fpdest_KML_plan);
				fclose(fpdest_KML_plan);

				dest_path_track_point[0] = '\0';
				dest_path_KML_track_point[0] = '\0';
				dest_path_flight_plan[0] = '\0';
				dest_path_KML_flight_plan[0] = '\0';
			}

			// Retrieve origin airport
			get_token(str, orig, ',', SUM_ORIG, 200);

			// Retrieve destination airport
			get_token(str, dest, ',', SUM_DEST, 200);

			if(!strcmp(orig, desired_orig) && !strcmp(dest, desired_dest)) {
				get_token(str, key, ',', SUM_RECORD_KEY, 200);
				fprintf(fpstatus, "Match found: Record #: %s, Origin: %s, Destination: %s\n", key, orig, dest);
				found_match = 1;
			}
		}
		if(str[0] == TRACK_POINT && found_match == 1) {

			// get time stamp
			get_token(str, time_stamp, ',', TRK_TIME_STAMP, 200);

			// get aircraft ID
			get_token(str, ac_id, ',', TRK_AC_ID, 200);

			// get longitude
			get_token(str, ac_long, ',', TRK_AC_LONG, 200);

			// get latitude
			get_token(str, ac_lat, ',', TRK_AC_LAT, 200);

			// get the flight level string and convert to float, multiply * 100, and convert back to string
			get_token(str, ac_alt, ',', TRK_AC_ALT, 200);
			alt_value = strtod(ac_alt, NULL);
			alt_value *= 100;
			sprintf(ac_alt, "%d", (int) alt_value);

			// get aircraft ground speed
			get_token(str, ac_gnd_spd, ',', TRK_AC_GND_SPD, 200);

			// get aircraft course
			get_token(str, ac_course, ',', TRK_AC_COURSE, 200);
			
			//If first track point of the flight
			if(!track_point_count++) {
				// Format the output file name, includes: origin, destination, aircraft ID
				strcpy(dest_path_track_point, dest_path_header);
				strcpy(dest_path_KML_track_point, dest_path_header);

				strcat(dest_path_track_point, desired_orig);
				strcat(dest_path_track_point, "_");
				strcat(dest_path_track_point, desired_dest);
				strcat(dest_path_track_point, "_");

				strcat(dest_path_KML_track_point, desired_orig);
				strcat(dest_path_KML_track_point, "_");
				strcat(dest_path_KML_track_point, desired_dest);
				strcat(dest_path_KML_track_point, "_");

				strcat(dest_path_track_point, ac_id);
				strcat(dest_path_track_point, "_trk.txt");
				strcat(dest_path_KML_track_point, ac_id);
				strcat(dest_path_KML_track_point, "_trk.kml");

				// Open destination KML file
				fpdest_KML_track = fopen(dest_path_KML_track_point, "w");
				if(fpdest_KML_track == NULL) {
					printf("KML Path:\n %s", dest_path_KML_track_point);
					perror("Error opening destination KML file");
					close_and_exit(-1, fpsource, fpdest_track, fpdest_plan, fpdest_KML_plan, fpdest_KML_plan, fpstatus);
				}

				// Open destination lat-long-alt file
				fpdest_track = fopen(dest_path_track_point, "w");
				if(fpdest_track  == NULL) {
					perror("Error opening destination Lat-Long-Alt file");
					close_and_exit(-1, fpsource, fpdest_track, fpdest_plan, fpdest_KML_plan, fpdest_KML_plan, fpstatus);
				}

				// Write the header text for the KML file
				write_kml_header(fpdest_KML_track);
			}
			// Write to output files
			fprintf(fpdest_KML_track, "\t\t%s,%s,%s\n", ac_long, ac_lat, ac_alt);
			fprintf(fpdest_track, "%s,%s,%s,%s,%s,%s,%s\n", ac_id, time_stamp, ac_lat, ac_long, ac_alt, ac_gnd_spd, ac_course);

		}
		if(str[0] == FLIGHT_PLAN && found_match == 1) {
			// get time stamp
			get_token(str, time_stamp, ',', TRK_TIME_STAMP, 500);
			// get aircraft ID
			get_token(str, ac_id, ',', TRK_AC_ID, 500);
			//get flight ID
			get_token(str, key, ',', TRK_RECORD_KEY,500);
			// get Waypoints
			get_token(str, waypoints, ',', PLAN_WAYPOINTS, 500);
				
			//If first flight plan entry of the flight
			if(!flight_plan_count++) {
				// Format the output file name, includes: origin, destination, aircraft ID
				strcpy(dest_path_flight_plan, dest_path_header);
				strcpy(dest_path_KML_flight_plan, dest_path_header);

				strcat(dest_path_flight_plan, desired_orig);
				strcat(dest_path_flight_plan, "_");
				strcat(dest_path_flight_plan, desired_dest);
				strcat(dest_path_flight_plan, "_");

				strcat(dest_path_KML_flight_plan, desired_orig);
				strcat(dest_path_KML_flight_plan, "_");
				strcat(dest_path_KML_flight_plan, desired_dest);
				strcat(dest_path_KML_flight_plan, "_");

				strcat(dest_path_flight_plan, ac_id);
				strcat(dest_path_flight_plan, "_fp.txt");
				strcat(dest_path_KML_flight_plan, ac_id);
				strcat(dest_path_KML_flight_plan, "_fp.kml");

				// Open destination KML file
				fpdest_KML_plan = fopen(dest_path_KML_flight_plan, "w");
				if(fpdest_KML_plan == NULL) {
					perror("Error opening destination KML (Plan) file");
					printf("KML Path:\n %s", dest_path_KML_flight_plan);
					close_and_exit(-1, fpsource, fpdest_track, fpdest_plan, fpdest_KML_plan, fpdest_KML_plan, fpstatus);
				}

				// Open destination lat-long-alt file
				fpdest_plan = fopen(dest_path_flight_plan, "w");
				if(fpdest_plan  == NULL) {
					perror("Error opening destination Waypoints file");
					close_and_exit(-1, fpsource, fpdest_track, fpdest_plan, fpdest_KML_plan, fpdest_KML_plan, fpstatus);
				}

				// Write the header text for the KML file
				write_kml_header(fpdest_KML_plan);
			}
			// Write to output files
			fprintf(fpdest_KML_plan, "\t\t%s\n", waypoints);
			fprintf(fpdest_plan, "%s,%s,%s,%s\n", ac_id, key, time_stamp, waypoints);

		}
	}

	printf("Complete\n");

	return 0;
}
