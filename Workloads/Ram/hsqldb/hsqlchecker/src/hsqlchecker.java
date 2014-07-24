import java.io.BufferedOutputStream;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.io.UnsupportedEncodingException;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

public class hsqlchecker {
	
	public static boolean isNull(String str) {
        return str == null ? true : false;
    }

    public static boolean isNullOrBlank(String param) {
        if (isNull(param) || param.trim().length() == 0) {
            return true;
        }
        return false;
    }
	
    public static boolean CheckForDurabilitySignal(String[] messages, String signal)
    {
    	for(int i=0;i<messages.length;i++)
    	{
    		String stripped = messages[i].trim();
    		if(stripped.contains(signal))
    		{
    			return true;
    		}
    	}
    	
    	return false;
    }
    
    public static void check(String[] stdouts) throws FileNotFoundException, UnsupportedEncodingException, SQLException
    {
    	try 
		{
			Class.forName("org.hsqldb.jdbc.JDBCDriver");
		} 
		catch (ClassNotFoundException e)
		{
			System.out.println(e.getMessage());
		}
    	
    	Connection con = null;
		int expectedCount = 100;
        try
        {
        	// Remove the lock file before doing anything. This can be waste of time when running the tests. 
        	File lckFile = new File("/home/ramnatthan/workload_snapshots/hsqldb/replayedsnapshot/mydatabase.lck");
        	if(lckFile.exists())
        	{
        		lckFile.delete();
        	}

        	Properties connectionProps = new Properties();
            connectionProps.put("user", "SA");
            connectionProps.put("password", "");
            
        	//String str = "jdbc:hsqldb:file:/home/ramnatthan/workspace/HSqlApp/databases/mydatabase";
        	String str = "jdbc:hsqldb:file:/home/ramnatthan/workload_snapshots/hsqldb/replayedsnapshot/mydatabase;shutdown=true";
        	con = DriverManager.getConnection(str,connectionProps);
        	
            PreparedStatement pst=con.prepareStatement("select * from contacts");
            pst.clearParameters();
            ResultSet rs=pst.executeQuery();
            boolean notProper = false;
       
            String improperOutput = "";
            int c = 0;
            while(rs.next()){
            	c++;
            	
            	String one = rs.getString(1);
            	String two = rs.getString(2);
            	String three = rs.getString(3);
            	
            	if(isNullOrBlank(one) || isNullOrBlank(two) || isNullOrBlank(three))
            	{
            		notProper = true;
            		
            		if(improperOutput == "")
            		{
            			improperOutput += "Corrupted data";
            		}
            	}
            	if(!one.startsWith("name") || !two.startsWith("email"))
            	{
            		notProper = true;
            		
            		if(improperOutput == "")
            		{
            			improperOutput += "Corrupted data";
            		}
            	}   	
            }
            
            if(c!=0 && c != expectedCount+1 ) notProper = true;
            
            PrintWriter writer = new PrintWriter("/tmp/short_output", "UTF-8");
            //String op = notProper ? "Improper Data! - Count was "+ (c)+ "- Problematic!" + improperOutput:"No problem - Checker! Read "+(c)+" rows properly";
            if (CheckForDurabilitySignal(stdouts, "TXNCommitDone"))
            {
            	if (c != expectedCount+1 )
            	{
            		if (c == 0)
            		{
            			writer.println("Durability signal found but retrieved " + c + " rows..which is not proper");
            		}
            		else
            		{
            			writer.println("Durability signal found but retrieved " + c + " rows..Possible corruption");
            		}
            	}
            	else
            	{
            		writer.println("Durability signal found. No problem");
            	}
            }
            else
            {
            	writer.println("Durability signal absent. Ignoring durability checks");
            }
            
            writer.close();
        } 
        catch(Exception e)
        {
        	PrintWriter writer = new PrintWriter("/tmp/short_output", "UTF-8");
        	if(e != null && e.getMessage() != null)
        	{
        		writer.write(e.getMessage());
        	}
        	
            e.printStackTrace();
            writer.close();
            //System.out.println(e.getMessage());
        }
        finally
        {
        	if (null != con)
        	{
	        	java.sql.Statement st = con.createStatement();
	    		st.execute("SHUTDOWN");
	    		System.out.println("shutdown done");
	        	con.close();        	    		
        	}
        }
    }
    
	public static void main(String[] args) throws SQLException, IOException
	{
		String[] parts = null;
		try{
            InputStream ips=new FileInputStream("/tmp/checkerparameters"); 
            InputStreamReader ipsr=new InputStreamReader(ips);
            BufferedReader br=new BufferedReader(ipsr);
            String line;
            
            // We just need to read one line
            line=br.readLine();
            parts = line.split(" ");
            
            br.close(); 
        }       
        catch (Exception e){
            System.out.println(e.toString());
        }
			
		/*FileWriter writer = new FileWriter("/tmp/commands", true);
		
		for(int j=0;parts!=null && j < parts.length; j++)
		{
		    writer.write(parts[j]);
		}
		
		writer.close();*/
		PrintWriter writer = new PrintWriter("/tmp/short_output", "UTF-8");
		if (null != parts)
			check(parts);
		else
		{
			writer.write("Params was null");
			writer.close();
		}
	}
}
