from flask import Flask, request, send_file, redirect, url_for, render_template
import os
import pandas as pd

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp/'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}

@app.route('/', methods=['GET'])
def index():
    # Render the HTML page for file upload
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the file part is present in the request
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']
        group_name = request.form['group_name']

        # Check if a file is selected and it has the allowed extension
        if file.filename == '' or not allowed_file(file.filename):
            return redirect(request.url)

        # Save the uploaded file to a temporary directory
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)

        # Filter the exporters from the Excel file
        filtered_data = filter_exporters(filename, group_name)

        # Generate the bookmarks HTML
        bookmarks_html = generate_bookmarks_html(filtered_data)
        
        # Define the filename for the bookmarks HTML file
        processed_filename = f"bookmarks_{group_name}.html"
        processed_filepath = os.path.join(app.config['UPLOAD_FOLDER'], processed_filename)

        # Save the bookmarks HTML to a file
        with open(processed_filepath, 'w', encoding='utf-8') as bookmarks_file:
            bookmarks_file.write(bookmarks_html)

        # Redirect the user to the download route
        return redirect(url_for('download_file', filename=processed_filename))

    # If the request method is not POST or other error conditions
    return 'File upload error'

def filter_exporters(filepath, group_name):
    # Read the Excel file
    df = pd.read_excel(filepath, engine='openpyxl')

    # Define the exporters to look for
    exporters = ['exporter_aes', 'exporter_avayasbc', 'exporter_acm']

    # Filter the DataFrame for rows that contain the specified exporters
    filtered_rows = []
    for exporter in exporters:
        # Check if the exporter columns exist in the DataFrame
        for col in ['Exporter_name_app', 'Exporter_name_app_2']:
            if col in df.columns:
                # Filter rows where the column contains the exporter
                matching_rows = df[df[col].str.contains(exporter, na=False)]
                # Extract necessary information from each row
                for _, row in matching_rows.iterrows():
                    filtered_rows.append({
                        'Group Name': group_name,
                        'Country': row['Country'],
                        'Location': row['Location'],
                        'Exporter Type': exporter,
                        'IP Address': row['IP Address']
                    })

    return filtered_rows

def generate_bookmarks_html(filtered_data):
    # Start the HTML string for the bookmarks
    bookmarks_html = "<!DOCTYPE NETSCAPE-Bookmark-file-1>\n"
    bookmarks_html += "<META HTTP-EQUIV=\"Content-Type\" CONTENT=\"text/html; charset=UTF-8\">\n"
    bookmarks_html += "<TITLE>Bookmarks</TITLE>\n"
    bookmarks_html += "<H1>Bookmarks Menu</H1>\n"
    bookmarks_html += "<DL><p>\n"
    
    # Add Group Name folders
    for group in set(item['Group Name'] for item in filtered_data):
        bookmarks_html += f"    <DT><H3>{group}</H3>\n"
        bookmarks_html += "    <DL><p>\n"
        
        # Add Country folders
        for country in set(item['Country'] for item in filtered_data if item['Group Name'] == group):
            bookmarks_html += f"        <DT><H3>{country}</H3>\n"
            bookmarks_html += "        <DL><p>\n"
            
            # Add Location folders
            for location in set(item['Location'] for item in filtered_data if item['Group Name'] == group and item['Country'] == country):
                bookmarks_html += f"            <DT><H3>{location}</H3>\n"
                bookmarks_html += "            <DL><p>\n"
                
                # Add exporter bookmarks
                for item in filtered_data:
                    if item['Group Name'] == group and item['Country'] == country and item['Location'] == location:
                        exporter_type = item['Exporter Type'].split('_')[-1]  # Extract the type from the full exporter name
                        url = f"https://{item['IP Address']}"
                        bookmarks_html += f"                <DT><A HREF=\"{url}\">{exporter_type}</A>\n"
                
                bookmarks_html += "            </DL><p>\n"
            bookmarks_html += "        </DL><p>\n"
        bookmarks_html += "    </DL><p>\n"
    
    bookmarks_html += "</DL><p>\n"
    
    return bookmarks_html

@app.route('/downloads/<filename>', methods=['GET'])
def download_file(filename):
    download_folder = app.config['UPLOAD_FOLDER']
    file_path = os.path.join(download_folder, filename)
    
    if not os.path.isfile(file_path):
        return "File not found.", 404

    response = send_file(file_path, as_attachment=True, download_name=filename)
    os.remove(file_path)
    
    return response

if __name__ == '__main__':
    app.run(debug=True)
